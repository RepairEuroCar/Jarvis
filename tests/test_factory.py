<<<<<<< HEAD
=======

>>>>>>> main
from jarvis.brain import ThoughtProcessorFactory
from jarvis.processors import LogicalThoughtProcessor


def test_factory_creates_logical_processor():
    proc = ThoughtProcessorFactory.create("logical")
    assert isinstance(proc, LogicalThoughtProcessor)
