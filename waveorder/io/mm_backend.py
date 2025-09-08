"""
Micro-Manager backend abstraction layer.

This module provides a clean interface for Micro-Manager functionality,
isolating all pycro-manager dependencies to enable easy migration to pymmcore-plus.

The interface is designed to be backend-agnostic so that implementations
can be swapped without changing client code.
"""

import logging
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Union

import numpy as np


class MMBackendError(Exception):
    """Base exception for MM backend errors."""
    pass


class MMConnectionError(MMBackendError):
    """Error establishing connection to Micro-Manager."""
    pass


class MMAcquisitionError(MMBackendError):
    """Error during acquisition operations."""
    pass


class MMBackend(ABC):
    """Abstract base class for Micro-Manager backends."""
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to Micro-Manager."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to Micro-Manager."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to Micro-Manager."""
        pass
    
    @abstractmethod
    def get_core(self) -> Any:
        """Get the core object for device control."""
        pass
    
    @abstractmethod
    def snap_image(self) -> np.ndarray:
        """Snap a single image and return as numpy array."""
        pass
    
    @abstractmethod
    def snap_and_average(self, num_images: int = 10) -> float:
        """Snap multiple images and return average intensity."""
        pass
    
    @abstractmethod
    def is_live_mode_on(self) -> bool:
        """Check if live mode is currently on."""
        pass
    
    @abstractmethod
    def set_live_mode(self, enabled: bool) -> None:
        """Enable or disable live mode."""
        pass
    
    @abstractmethod
    def generate_acquisition_settings(
        self,
        channel_group: str,
        channels: Optional[List[str]] = None,
        zstart: Optional[float] = None,
        zend: Optional[float] = None,
        zstep: Optional[float] = None,
        save_dir: Optional[str] = None,
        prefix: Optional[str] = None,
        keep_shutter_open_channels: bool = False,
        keep_shutter_open_slices: bool = False,
    ) -> Dict[str, Any]:
        """Generate acquisition settings for MDA sequence."""
        pass
    
    @abstractmethod
    def run_acquisition(self, settings: Dict[str, Any]) -> None:
        """Run acquisition with given settings."""
        pass
    
    @abstractmethod
    def get_channel_exposure_time(self, channel_group: str, channel: str) -> float:
        """Get exposure time for a specific channel."""
        pass


class PycromanagerBackend(MMBackend):
    """Pycro-manager implementation of MM backend."""
    
    def __init__(self):
        self._core = None
        self._studio = None
        self._bridge = None
        self._snap_manager = None
        self._connected = False
    
    def connect(self) -> None:
        """Establish connection to Micro-Manager via pycro-manager."""
        try:
            from pycromanager import Core, Studio, zmq_bridge
            
            self._core = Core(convert_camel_case=False)
            self._studio = Studio(convert_camel_case=False)
            # Order is important: If the bridge is created before Core, Core will not work
            self._bridge = zmq_bridge._bridge._Bridge()
            
            # Get snap manager for image acquisition
            self._snap_manager = self._studio.live().getSnapLiveManager()
            
            self._connected = True
            logging.debug("Established ZMQ Bridge and found Core and Studio")
            
        except Exception as e:
            raise MMConnectionError(f"Failed to connect to Micro-Manager: {e}")
    
    def disconnect(self) -> None:
        """Close connection to Micro-Manager."""
        # pycro-manager connections are typically handled automatically
        self._core = None
        self._studio = None
        self._bridge = None
        self._snap_manager = None
        self._connected = False
    
    def is_connected(self) -> bool:
        """Check if connected to Micro-Manager."""
        return self._connected and self._core is not None
    
    def get_core(self) -> Any:
        """Get the core object for device control."""
        if not self._connected:
            raise MMConnectionError("Not connected to Micro-Manager")
        return self._core
    
    @contextmanager
    def _suspend_live_mode(self):
        """Context manager that suspends/unsuspends MM live mode."""
        if self._snap_manager is None:
            raise MMConnectionError("Snap manager not available")
        
        self._snap_manager.setSuspended(True)
        try:
            yield self._snap_manager
        finally:
            self._snap_manager.setSuspended(False)
    
    def snap_image(self) -> np.ndarray:
        """Snap a single image and return as numpy array."""
        if self._snap_manager is None:
            raise MMConnectionError("Snap manager not available")
        
        with self._suspend_live_mode():
            self._snap_manager.snap(True)
            time.sleep(0.3)  # Allow time for image capture
            
            # Get the image from the snap manager
            tagged_image = self._snap_manager.getTaggedImage()
            if tagged_image is None:
                raise MMAcquisitionError("Failed to capture image")
            
            # Convert to numpy array
            return np.array(tagged_image.pix)
    
    def snap_and_average(self, num_images: int = 10) -> float:
        """Snap multiple images and return average intensity."""
        intensities = []
        for _ in range(num_images):
            image = self.snap_image()
            intensities.append(np.mean(image))
        
        return np.mean(intensities)
    
    def is_live_mode_on(self) -> bool:
        """Check if live mode is currently on."""
        if self._snap_manager is None:
            return False
        return self._snap_manager.getIsLiveModeOn()
    
    def set_live_mode(self, enabled: bool) -> None:
        """Enable or disable live mode."""
        if self._snap_manager is None:
            raise MMConnectionError("Snap manager not available")
        self._snap_manager.setLiveModeOn(enabled)
    
    def generate_acquisition_settings(
        self,
        channel_group: str,
        channels: Optional[List[str]] = None,
        zstart: Optional[float] = None,
        zend: Optional[float] = None,
        zstep: Optional[float] = None,
        save_dir: Optional[str] = None,
        prefix: Optional[str] = None,
        keep_shutter_open_channels: bool = False,
        keep_shutter_open_slices: bool = False,
    ) -> Dict[str, Any]:
        """Generate acquisition settings for MDA sequence."""
        if not self._connected:
            raise MMConnectionError("Not connected to Micro-Manager")
        
        am = self._studio.getAcquisitionManager()
        ss = am.getAcquisitionSettings()
        app = self._studio.app()
        
        # Set basic parameters
        if save_dir:
            ss.save = True
            ss.root = save_dir
        if prefix:
            ss.prefix = prefix
        
        # Configure channels
        if channels:
            ss.useChannels = True
            ss.channels.clear()
            
            for channel in channels:
                try:
                    exposure = app.getChannelExposureTime(
                        channel_group, channel
                    )
                except:
                    exposure = 100.0  # Default exposure
                
                channel_spec = {
                    "config": channel,
                    "exposure": exposure,
                    "zOffset": 0.0,
                    "doZStack": True,
                    "skipFactorForZ": 0,
                    "useChannel": True,
                }
                ss.channels.add(app.getChannelSpec().fromJSONMetadata(str(channel_spec)))
        
        # Configure z-stack
        if zstart is not None and zend is not None and zstep is not None:
            ss.useSlices = True
            ss.sliceZStepUm = abs(zstep)
            ss.sliceZBottomUm = min(zstart, zend)
            ss.sliceZTopUm = max(zstart, zend)
        
        # Set shutter options
        ss.keepShutterOpenChannels = keep_shutter_open_channels
        ss.keepShutterOpenSlices = keep_shutter_open_slices
        
        # Convert to JSON for return
        return ss.toJSON()
    
    def run_acquisition(self, settings: Dict[str, Any]) -> None:
        """Run acquisition with given settings."""
        if not self._connected:
            raise MMConnectionError("Not connected to Micro-Manager")
        
        am = self._studio.getAcquisitionManager()
        
        # Convert settings back to SequenceSettings object
        ss = am.getAcquisitionSettings()
        ss_new = ss.fromJSON(settings)
        
        # Run the acquisition
        am.runAcquisitionWithSettings(ss_new, True)
        
        # Restore original settings
        am.setAcquisitionSettings(ss)
    
    def get_channel_exposure_time(self, channel_group: str, channel: str) -> float:
        """Get exposure time for a specific channel."""
        if not self._connected:
            raise MMConnectionError("Not connected to Micro-Manager")
        
        app = self._studio.app()
        try:
            return app.getChannelExposureTime(channel_group, channel)
        except Exception as e:
            raise MMAcquisitionError(f"Failed to get exposure time for {channel}: {e}")


# Global backend instance
_backend_instance: Optional[MMBackend] = None


def get_mm_backend() -> MMBackend:
    """Get the global MM backend instance."""
    global _backend_instance
    if _backend_instance is None:
        _backend_instance = PycromanagerBackend()
    return _backend_instance


def set_mm_backend(backend: MMBackend) -> None:
    """Set the global MM backend instance (for testing or migration)."""
    global _backend_instance
    _backend_instance = backend


def connect_to_mm() -> MMBackend:
    """Connect to Micro-Manager and return backend instance."""
    backend = get_mm_backend()
    backend.connect()
    return backend


def disconnect_from_mm() -> None:
    """Disconnect from Micro-Manager."""
    backend = get_mm_backend()
    backend.disconnect()