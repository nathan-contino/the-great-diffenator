import asyncio
from viam.module.module import Module
from viam.resource.registry import Registry, ResourceCreatorRegistration
try:
    from models.pixel_diff import DiffVision
except ModuleNotFoundError:
    # when running as local module with run.sh
    from .models.pixel_diff import DiffVision

if __name__ == '__main__':
    asyncio.run(Module.run_from_registry())
