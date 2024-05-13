# INTERSECT-SDK

The INTERSECT-SDK is a framework for microservices to integrate themselves into the wider INTERSECT ecosystem.

Please note that this README is currently a work in progress.

## What is INTERSECT?

INTERSECT was designed as a specific usecase - as an open federated hardware/software architecture for the laboratory of the future, which connects scientific instruments, robot-controlled laboratories and edge/center computing/data resources to enable autonomous experiments, self-driving laboratories, smart manufacturing, and AI-driven design, discovery and evaluation.

## What are the core design philosophies of the SDK?

- Event-driven architecture
- Support core interaction types: request/response, events, commands, statuses
- Borrows several concepts from [AsyncAPI](https://www.asyncapi.com/docs/reference/specification/latest), and intends to support multiple different protocols. Currently, we support MQTT 3.1.1 and AMQP 0.9.1, but other protocols will be supported as well.
- Users automatically generate schema from code; schemas are part of the core contract of an INTERSECT microservice, and both external inputs and microservice outputs are required to uphold this contract.
