from fastapi import FastAPI, Request
from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectService,
    IntersectServiceConfig,
    IntersectEventDefinition,
    intersect_event,
    intersect_status,
)

class IntersectEventEmitter(IntersectBaseCapabilityImplementation):
    @intersect_status
    def status(self) -> str:
        return 'Up'
    
    @intersect_event(events={'ingestion_event': IntersectEventDefinition(event_type=str)})
    def ingestion_event(self, event: str) -> str:
        self.intersect_sdk_emit_event('ingestion_event', event)
        return event
    
if __name__ == "__main__":
    from_config_file = {
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 1883,
                'protocol': 'mqtt3.1.1',
            },
        ],
    }
    config = IntersectServiceConfig(
        hierarchy=HierarchyConfig(
            organization='restful-organization',
            facility='restful-facility',
            system='restful-system',
            subsystem='restful-subsystem',
            service='restful-service',
        ),
        **from_config_file,
    )

    capability = IntersectEventEmitter()
    capability.capability_name = 'IngestionEmitter'

    service = IntersectService([capability], config)
    service.startup()
    app = FastAPI()

    @app.get("/health")
    async def health_check():
        """
        Endpoint for health checks. Returns 200 if healthy.
        """
        return {"status":"ok"}

    @app.post("/{path:path}")
    async def generic_post(path: str, request: Request):
        """
        Generic POST endpoint that accepta data on any path.
        Returns the received data and the requested path.
        """
        data = await request.json()
        capability.ingestion_event(data)
        return {"path": path, "data": data}


    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)