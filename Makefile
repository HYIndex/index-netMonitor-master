init: taskqueue.hpp initialQueue.cpp
	g++ initialQueue.cpp -o initialQueue -lhiredis
monitor: taskqueue.hpp monitor.cpp
	g++ monitor.cpp -o monitor -lhiredis