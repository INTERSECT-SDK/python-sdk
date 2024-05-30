# INTERSECT-SDK

The INTERSECT-SDK is a framework for microservices to integrate themselves into the wider Interconnected Science Ecosystem (INTERSECT).

Please note that this README is currently a work in progress.

## What is INTERSECT?
[INTERSECT](https://www.ornl.gov/intersect) was designed as a specific usecase - as an open federated hardware/software architecture for the laboratory of the future, which connects scientific instruments, robot-controlled laboratories and edge/center computing/data resources to enable autonomous experiments, self-driving laboratories, smart manufacturing, and AI-driven design, discovery and evaluation.

## What are the core design philosophies of the SDK?

- Event-driven architecture
- Support core interaction types: request/response, events, commands, statuses
- Borrows several concepts from [AsyncAPI](https://www.asyncapi.com/docs/reference/specification/latest), and intends to support multiple different protocols. Currently, we support MQTT 3.1.1 and AMQP 0.9.1, but other protocols will be supported as well.
- Users automatically generate schema from code; schemas are part of the core contract of an INTERSECT microservice, and both external inputs and microservice outputs are required to uphold this contract.

## Authors

INTERSECT SDK was created by its [contributors](https://github.com/intersect-sdk/python-sdk/graphs/contributors).

### Citing INTERSECT-SDK

If you are referencing INTERSECT-SDK in a publication, please cite the following paper:

 * Addi Malviya Thakur, Seth Hitefield, Marshall McDonnell, Matthew Wolf, Richard Archibald, Lance Drane, Kevin Roccapriore, Maxim Ziatdinov, Jesse McGaha, Robert Smith, John Hetrick, Mark Abraham, Sergey Yakubov, Greg Watson, Ben Chance, Clara Nguyen, Matthew Baker, Robert Michael, Elke Arenholz & Ben Mintz. Towards a Software Development Framework for Interconnected Science Ecosystems. In: Doug, K., Al, G., Pophale, S., Liu, H., Parete-Koon, S. (eds) Accelerating Science and Engineering Discoveries Through Integrated Research Infrastructure for Experiment, Big Data, Modeling and Simulation. SMC 2022. Communications in Computer and Information Science, vol 1690. Springer, Cham. https://doi.org/10.1007/978-3-031-23606-8_13

On GitHub, you can copy this citation in APA or BibTeX format via the "Cite this repository" button. Or, see the comments in `CITATION.cff` for the raw BibTeX.

## Acknowledgements

The INTERSECT-SDK development has received funding support / sponsorship from the following:

  * Laboratory Directed Research and Development Program of Oak Ridge National Laboratory, managed by UT-Battelle, LLC, for the U. S. Department of Energy.
