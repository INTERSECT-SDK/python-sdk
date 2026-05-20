from hashlib import sha384


def get_service_queue_name(routing_key: str) -> str:
    """Generate a valid queue name from the routing key.

    We want to always be able to generate the same queue name from the routing key every time,
    so we don't use UUIDs or want the broker to generate a key name.

    We must also keep the length under 128 characters.

    See https://www.rabbitmq.com/docs/queues#names for a complete reference.
    """
    return sha384(routing_key.encode()).hexdigest()
