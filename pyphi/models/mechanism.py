#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# models/mechanism.py

"""Mechanism-level objects."""

import numpy as np

from . import cmp, fmt
from .. import config, connectivity, distribution, utils
from ..direction import Direction
from ..exceptions import WrongDirectionError

# pylint: disable=too-many-arguments,too-many-instance-attributes

_ria_attributes = ['phi', 'direction', 'mechanism', 'purview', 'partition',
                   'repertoire', 'partitioned_repertoire']


class RepertoireIrreducibilityAnalysis(cmp.Orderable):
    """An analysis of the irreducibility (|small_phi|) of a mechanism over a
    purview, for a given partition, in one temporal direction.

    These can be compared with the built-in Python comparison operators (``<``,
    ``>``, etc.). First, |small_phi| values are compared. Then, if these are
    equal up to |PRECISION|, the size of the mechanism is compared (see the
    |PICK_SMALLEST_PURVIEW| option in |config|.)
    """

    def __init__(self, phi, direction, mechanism, purview, partition,
                 repertoire, partitioned_repertoire,
                 subsystem=None):
        self._phi = phi
        self._direction = direction
        self._mechanism = mechanism
        self._purview = purview
        self._partition = partition

        def _repertoire(repertoire):
            if repertoire is None:
                return None
            return np.array(repertoire)

        self._repertoire = _repertoire(repertoire)
        self._partitioned_repertoire = _repertoire(partitioned_repertoire)

        # Optional subsystem - only used to generate nice labeled reprs
        self._subsystem = subsystem

    @property
    def phi(self):
        """float: This is the difference between the mechanism's unpartitioned
        and partitioned repertoires.
        """
        return self._phi

    @property
    def direction(self):
        """Direction: |CAUSE| or |EFFECT|."""
        return self._direction

    @property
    def mechanism(self):
        """tuple[int]: The mechanism that was analyzed."""
        return self._mechanism

    @property
    def purview(self):
        """tuple[int]: The purview over which the the mechanism was
        analyzed.
        """
        return self._purview

    @property
    def partition(self):
        """KPartition: The partition of the mechanism-purview pair that was
        analyzed.
        """
        return self._partition

    @property
    def repertoire(self):
        """np.ndarray: The repertoire of the mechanism over the purview."""
        return self._repertoire

    @property
    def partitioned_repertoire(self):
        """np.ndarray: The partitioned repertoire of the mechanism over the
        purview. This is the product of the repertoires of each part of the
        partition.
        """
        return self._partitioned_repertoire

    @property
    def subsystem(self):
        """Subsystem: The |Subsystem| the mechanism belongs to."""
        return self._subsystem

    unorderable_unless_eq = ['direction']

    def order_by(self):
        if config.PICK_SMALLEST_PURVIEW:
            return [self.phi, len(self.mechanism), -len(self.purview)]

        return [self.phi, len(self.mechanism), len(self.purview)]

    def __eq__(self, other):
        # We don't consider the partition and partitioned repertoire in
        # checking for RIA equality.
        attrs = ['phi', 'direction', 'mechanism', 'purview',
                 'repertoire']
        return cmp.general_eq(self, other, attrs)

    def __bool__(self):
        """A |RepertoireIrreducibilityAnalysis| is ``True`` if it has
        |small_phi > 0|.
        """
        return not utils.eq(self.phi, 0)

    def __hash__(self):
        return hash((self.phi,
                     self.direction,
                     self.mechanism,
                     self.purview,
                     utils.np_hash(self.repertoire)))

    def __repr__(self):
        return fmt.make_repr(self, _ria_attributes)

    def __str__(self):
        return ("Repertoire irreducibility analysis\n" +
                fmt.indent(fmt.fmt_ria(self)))

    def to_json(self):
        return {attr: getattr(self, attr) for attr in _ria_attributes}


def _null_ria(direction, mechanism, purview, repertoire=None):
    """The irreducibility analysis for a reducible mechanism."""
    # TODO Use properties here to infer mechanism and purview from
    # partition yet access them with .mechanism and .partition
    return RepertoireIrreducibilityAnalysis(
        direction=direction,
        mechanism=mechanism,
        purview=purview,
        partition=None,
        repertoire=repertoire,
        partitioned_repertoire=None,
        phi=0.0
    )


# =============================================================================

class MaximallyIrreducibleCauseOrEffect(cmp.Orderable):
    """A maximally irreducible cause or effect (MICE).

    These can be compared with the built-in Python comparison operators (``<``,
    ``>``, etc.). First, |small_phi| values are compared. Then, if these are
    equal up to |PRECISION|, the size of the mechanism is compared (see the
    |PICK_SMALLEST_PURVIEW| option in |config|.)
    """

    def __init__(self, ria):
        self._ria = ria

    @property
    def phi(self):
        """float: The difference between the mechanism's unpartitioned and
        partitioned repertoires.
        """
        return self._ria.phi

    @property
    def direction(self):
        """Direction: |CAUSE| or |EFFECT|."""
        return self._ria.direction

    @property
    def mechanism(self):
        """list[int]: The mechanism for which the MICE is evaluated."""
        return self._ria.mechanism

    @property
    def purview(self):
        """list[int]: The purview over which this mechanism's |small_phi| is
        maximal.
        """
        return self._ria.purview

    @property
    def mip(self):
        """KPartition: The partition that makes the least difference to the
        mechanism's repertoire.
        """
        return self._ria.partition

    @property
    def repertoire(self):
        """np.ndarray: The unpartitioned repertoire of the mechanism over the
        purview.
        """
        return self._ria.repertoire

    @property
    def partitioned_repertoire(self):
        """np.ndarray: The partitioned repertoire of the mechanism over the
        purview.
        """
        return self._ria.partitioned_repertoire

    @property
    def ria(self):
        """RepertoireIrreducibilityAnalysis: The irreducibility analysis for
        this mechanism.
        """
        return self._ria

    def __repr__(self):
        return fmt.make_repr(self, ['ria'])

    def __str__(self):
        return (
            "Maximally-irreducible {}\n".format(str(self.direction).lower()) +
            fmt.indent(fmt.fmt_ria(self.ria, mip=True))
        )

    unorderable_unless_eq = \
        RepertoireIrreducibilityAnalysis.unorderable_unless_eq

    def order_by(self):
        return self.ria.order_by()

    def __eq__(self, other):
        return self.ria == other.ria

    def __hash__(self):
        return hash(('MICE', self._ria))

    def to_json(self):
        return {'ria': self.ria}

    def _relevant_connections(self, subsystem):
        """Identify connections that “matter” to this concept.

        For a |MIC|, the important connections are those which connect the
        purview to the mechanism; for a |MIE| they are the connections from the
        mechanism to the purview.

        Returns an |N x N| matrix, where `N` is the number of nodes in this
        corresponding subsystem, that identifies connections that “matter” to
        this MICE:

        ``direction == Direction.CAUSE``:
            ``relevant_connections[i,j]`` is ``1`` if node ``i`` is in the
            cause purview and node ``j`` is in the mechanism (and ``0``
            otherwise).

        ``direction == Direction.EFFECT``:
            ``relevant_connections[i,j]`` is ``1`` if node ``i`` is in the
            mechanism and node ``j`` is in the effect purview (and ``0``
            otherwise).

        Args:
            subsystem (Subsystem): The |Subsystem| of this MICE.

        Returns:
            np.ndarray: A |N x N| matrix of connections, where |N| is the size
            of the network.

        Raises:
            ValueError: If ``direction`` is invalid.
        """
        _from, to = self.direction.order(self.mechanism, self.purview)
        return connectivity.relevant_connections(subsystem.network.size,
                                                 _from, to)

    # TODO: pass in `cut` instead? We can infer
    # subsystem indices from the cut itself, validate, and check.
    def damaged_by_cut(self, subsystem):
        """Return ``True`` if this MICE is affected by the subsystem's cut.

        The cut affects the MICE if it either splits the MICE's mechanism
        or splits the connections between the purview and mechanism.
        """
        return (subsystem.cut.splits_mechanism(self.mechanism) or
                np.any(self._relevant_connections(subsystem) *
                       subsystem.cut.cut_matrix(subsystem.network.size) == 1))


class MaximallyIrreducibleCause(MaximallyIrreducibleCauseOrEffect):
    """A maximally irreducible cause (MIC).

    These can be compared with the built-in Python comparison operators (``<``,
    ``>``, etc.). First, |small_phi| values are compared. Then, if these are
    equal up to |PRECISION|, the size of the mechanism is compared (see the
    |PICK_SMALLEST_PURVIEW| option in |config|.)
    """

    def __init__(self, ria):
        if ria.direction != Direction.CAUSE:
            raise WrongDirectionError('A MIC must be initialized with a RIA '
                                      'in the cause direction.')
        super().__init__(ria)

    @property
    def direction(self):
        """Direction: |CAUSE|."""
        return self._ria.direction


class MaximallyIrreducibleEffect(MaximallyIrreducibleCauseOrEffect):
    """A maximally irreducible effect (MIE).

    These can be compared with the built-in Python comparison operators (``<``,
    ``>``, etc.). First, |small_phi| values are compared. Then, if these are
    equal up to |PRECISION|, the size of the mechanism is compared (see the
    |PICK_SMALLEST_PURVIEW| option in |config|.)
    """

    def __init__(self, ria):
        if ria.direction != Direction.EFFECT:
            raise WrongDirectionError('A MIE must be initialized with a RIA '
                                      'in the effect direction.')
        super().__init__(ria)

    @property
    def direction(self):
        """Direction: |EFFECT|."""
        return self._ria.direction


# =============================================================================

_concept_attributes = ['phi', 'mechanism', 'cause', 'effect', 'subsystem']


# TODO: make mechanism a property
# TODO: make phi a property
class Concept(cmp.Orderable):
    """The maximally irreducible cause and effect specified by a mechanism.

    These can be compared with the built-in Python comparison operators (``<``,
    ``>``, etc.). First, |small_phi| values are compared. Then, if these are
    equal up to |PRECISION|, the size of the mechanism is compared.

    Attributes:
        mechanism (tuple[int]): The mechanism that the concept consists of.
        cause (MaximallyIrreducibleCause): The |MIC| representing the
            maximally-irreducible cause of this concept.
        effect (MaximallyIrreducibleEffect): The |MIE| representing the
            maximally-irreducible effect of this concept.
        subsystem (Subsystem): This concept's parent subsystem.
        time (float): The number of seconds it took to calculate.
    """

    def __init__(self, mechanism=None, cause=None, effect=None,
                 subsystem=None, time=None):
        self.mechanism = mechanism
        self.cause = cause
        self.effect = effect
        self.subsystem = subsystem
        self.time = time

    def __repr__(self):
        return fmt.make_repr(self, _concept_attributes)

    def __str__(self):
        return fmt.fmt_concept(self)

    @property
    def phi(self):
        """float: The size of the concept.

        This is the minimum of the |small_phi| values of the concept's |MIC|
        and |MIE|.
        """
        return min(self.cause.phi, self.effect.phi)

    @property
    def cause_purview(self):
        """tuple[int]: The cause purview."""
        return getattr(self.cause, 'purview', None)

    @property
    def effect_purview(self):
        """tuple[int]: The effect purview."""
        return getattr(self.effect, 'purview', None)

    @property
    def cause_repertoire(self):
        """np.ndarray: The cause repertoire."""
        return getattr(self.cause, 'repertoire', None)

    @property
    def effect_repertoire(self):
        """np.ndarray: The effect repertoire."""
        return getattr(self.effect, 'repertoire', None)

    unorderable_unless_eq = ['subsystem']

    def order_by(self):
        return [self.phi, len(self.mechanism)]

    def __eq__(self, other):
        return (self.phi == other.phi and
                self.mechanism == other.mechanism and
                (utils.state_of(self.mechanism, self.subsystem.state) ==
                 utils.state_of(self.mechanism, other.subsystem.state)) and
                self.cause_purview == other.cause_purview and
                self.effect_purview == other.effect_purview and
                self.eq_repertoires(other) and
                self.subsystem.network == other.subsystem.network)

    def __hash__(self):
        return hash((self.phi,
                     self.mechanism,
                     utils.state_of(self.mechanism, self.subsystem.state),
                     self.cause_purview,
                     self.effect_purview,
                     utils.np_hash(self.cause_repertoire),
                     utils.np_hash(self.effect_repertoire),
                     self.subsystem.network))

    def __bool__(self):
        """A concept is ``True`` if |small_phi > 0|."""
        return not utils.eq(self.phi, 0)

    def eq_repertoires(self, other):
        """Return whether this concept has the same repertoires as another.

        .. warning::
            This only checks if the cause and effect repertoires are equal as
            arrays; mechanisms, purviews, or even the nodes that the mechanism
            and purview indices refer to, might be different.
        """
        return (
            np.array_equal(self.cause_repertoire, other.cause_repertoire) and
            np.array_equal(self.effect_repertoire, other.effect_repertoire))

    def emd_eq(self, other):
        """Return whether this concept is equal to another in the context of
        an EMD calculation.
        """
        return (self.phi == other.phi and
                self.mechanism == other.mechanism and
                self.eq_repertoires(other))

    # TODO Rename to expanded_cause_repertoire, etc
    def expand_cause_repertoire(self, new_purview=None):
        """See |Subsystem.expand_repertoire()|."""
        return self.subsystem.expand_cause_repertoire(
            self.cause.repertoire, new_purview)

    def expand_effect_repertoire(self, new_purview=None):
        """See |Subsystem.expand_repertoire()|."""
        return self.subsystem.expand_effect_repertoire(
            self.effect.repertoire, new_purview)

    def expand_partitioned_cause_repertoire(self):
        """See |Subsystem.expand_repertoire()|."""
        return self.subsystem.expand_cause_repertoire(
            self.cause.ria.partitioned_repertoire)

    def expand_partitioned_effect_repertoire(self):
        """See |Subsystem.expand_repertoire()|."""
        return self.subsystem.expand_effect_repertoire(
            self.effect.ria.partitioned_repertoire)

    def to_json(self):
        """Return a JSON-serializable representation."""
        dct = {
            attr: getattr(self, attr)
            for attr in _concept_attributes + ['time']
        }
        # These flattened, little-endian repertoires are passed to `vphi` via
        # `phiserver`.
        dct.update({
            'expanded_cause_repertoire': distribution.flatten(
                self.expand_cause_repertoire()),
            'expanded_effect_repertoire': distribution.flatten(
                self.expand_effect_repertoire()),
            'expanded_partitioned_cause_repertoire': distribution.flatten(
                self.expand_partitioned_cause_repertoire()),
            'expanded_partitioned_effect_repertoire': distribution.flatten(
                self.expand_partitioned_effect_repertoire()),
        })
        return dct

    @classmethod
    def from_json(cls, dct):
        # Remove extra attributes
        del dct['phi']
        del dct['expanded_cause_repertoire']
        del dct['expanded_effect_repertoire']
        del dct['expanded_partitioned_cause_repertoire']
        del dct['expanded_partitioned_effect_repertoire']

        return cls(**dct)
