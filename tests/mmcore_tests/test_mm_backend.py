"""Tests for the MM backend abstraction layer."""

from typing import Dict
from unittest.mock import MagicMock, Mock, patch
import numpy as np
import pytest

from waveorder.io.mm_backend import PycromanagerBackend, MMConnectionError, MMAcquisitionError


class TestPycromanagerBackend:
    """Test the PycromanagerBackend implementation."""

    @pytest.fixture
    def mock_core(self):
        """Mock Core object."""
        return MagicMock()

    @pytest.fixture 
    def mock_studio(self):
        """Mock Studio object."""
        mock_studio = MagicMock()
        mock_studio.live.return_value.getSnapLiveManager.return_value = MagicMock()
        return mock_studio

    @pytest.fixture
    def mock_bridge(self):
        """Mock ZMQ bridge."""
        return MagicMock()

    @pytest.fixture
    def backend(self, mock_core, mock_studio, mock_bridge):
        """PycromanagerBackend instance with mocked dependencies."""
        with patch('waveorder.io.mm_backend.Core') as mock_core_cls, \
             patch('waveorder.io.mm_backend.Studio') as mock_studio_cls, \
             patch('waveorder.io.mm_backend.zmq_bridge') as mock_zmq:
            
            mock_core_cls.return_value = mock_core
            mock_studio_cls.return_value = mock_studio
            mock_zmq._bridge._Bridge.return_value = mock_bridge
            
            backend = PycromanagerBackend()
            backend.connect()
            return backend

    def test_connect_success(self, mock_core, mock_studio, mock_bridge):
        """Test successful connection to MM."""
        with patch('waveorder.io.mm_backend.Core') as mock_core_cls, \
             patch('waveorder.io.mm_backend.Studio') as mock_studio_cls, \
             patch('waveorder.io.mm_backend.zmq_bridge') as mock_zmq:
            
            mock_core_cls.return_value = mock_core
            mock_studio_cls.return_value = mock_studio
            mock_zmq._bridge._Bridge.return_value = mock_bridge
            
            backend = PycromanagerBackend()
            backend.connect()
            
            assert backend.is_connected()
            assert backend.get_core() == mock_core

    def test_connect_failure(self):
        """Test connection failure handling."""
        with patch('waveorder.io.mm_backend.Core') as mock_core_cls:
            mock_core_cls.side_effect = Exception("Connection failed")
            
            backend = PycromanagerBackend()
            with pytest.raises(MMConnectionError, match="Failed to connect to Micro-Manager"):
                backend.connect()

    def test_disconnect(self, backend):
        """Test disconnection."""
        backend.disconnect()
        assert not backend.is_connected()

    def test_snap_image(self, backend):
        """Test image snapping."""
        # Mock the snap manager and tagged image
        mock_tagged_image = Mock()
        mock_tagged_image.pix = np.random.randint(0, 4096, size=(100, 100))
        backend._snap_manager.snap = Mock()
        backend._snap_manager.getTaggedImage.return_value = mock_tagged_image
        backend._snap_manager.setSuspended = Mock()
        
        image = backend.snap_image()
        
        assert isinstance(image, np.ndarray)
        backend._snap_manager.snap.assert_called_once_with(True)
        backend._snap_manager.getTaggedImage.assert_called_once()

    def test_snap_and_average(self, backend):
        """Test snap and average functionality."""
        # Mock snap_image to return consistent images
        test_image = np.ones((10, 10)) * 100
        backend.snap_image = Mock(return_value=test_image)
        
        avg_intensity = backend.snap_and_average(num_images=5)
        
        assert avg_intensity == 100.0
        assert backend.snap_image.call_count == 5

    def test_live_mode_control(self, backend):
        """Test live mode control."""
        backend._snap_manager.getIsLiveModeOn.return_value = False
        backend._snap_manager.setLiveModeOn = Mock()
        
        assert not backend.is_live_mode_on()
        
        backend.set_live_mode(True)
        backend._snap_manager.setLiveModeOn.assert_called_once_with(True)

    def test_generate_acquisition_settings(self, backend):
        """Test acquisition settings generation."""
        # Mock the acquisition manager and related objects
        mock_am = Mock()
        mock_ss = Mock()
        mock_app = Mock()
        
        backend._studio.getAcquisitionManager.return_value = mock_am
        mock_am.getAcquisitionSettings.return_value = mock_ss
        backend._studio.app.return_value = mock_app
        mock_ss.toJSON.return_value = {"test": "settings"}
        
        settings = backend.generate_acquisition_settings(
            channel_group="TestGroup",
            channels=["State0", "State1"],
            zstart=0.0,
            zend=10.0,
            zstep=1.0,
            save_dir="/test/dir",
            prefix="test"
        )
        
        assert isinstance(settings, dict)
        backend._studio.getAcquisitionManager.assert_called_once()

    def test_run_acquisition(self, backend):
        """Test acquisition execution."""
        mock_am = Mock()
        mock_ss = Mock()
        
        backend._studio.getAcquisitionManager.return_value = mock_am
        mock_am.getAcquisitionSettings.return_value = mock_ss
        
        settings = {"test": "settings"}
        backend.run_acquisition(settings)
        
        backend._studio.getAcquisitionManager.assert_called_once()
        mock_am.runAcquisitionWithSettings.assert_called_once()

    def test_get_channel_exposure_time(self, backend):
        """Test channel exposure time retrieval."""
        mock_app = Mock()
        backend._studio.app.return_value = mock_app
        mock_app.getChannelExposureTime.return_value = 100.0
        
        exposure = backend.get_channel_exposure_time("TestGroup", "State0")
        
        assert exposure == 100.0
        mock_app.getChannelExposureTime.assert_called_once_with("TestGroup", "State0")

    def test_not_connected_errors(self):
        """Test that operations fail when not connected."""
        backend = PycromanagerBackend()
        
        with pytest.raises(MMConnectionError):
            backend.get_core()
            
        with pytest.raises(MMConnectionError):
            backend.generate_acquisition_settings("TestGroup")