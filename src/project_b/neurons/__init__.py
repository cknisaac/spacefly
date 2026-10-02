"""Explicit temporal neuron dynamics; M1 contains only LIF."""

from .lif import LIFParameters, advance_lif

__all__ = ["LIFParameters", "advance_lif"]
