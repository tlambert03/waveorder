# Migration Report: Replacing pycro-manager with pymmcore-plus in waveorder

## Executive Summary

This report analyzes the current usage of pycro-manager in waveorder and
provides a comprehensive plan for migrating to pymmcore-plus. The migration
involves replacing ZMQ-based remote communication with Micro-Manager Java GUI
with direct Python bindings to MMCoreAndDevices.

## 1. Current Usage of pycro-manager in waveorder

### 1.1 Import Analysis

**Files using pycro-manager:**

- `waveorder/acq/acq_functions.py:10` - `from pycromanager import Studio`
- `waveorder/plugin/main_widget.py:26` - `from pycromanager import Core, Studio, zmq_bridge`
- `waveorder/scripts/repeat-cal-acq-rec.py:8` - `from pycromanager import Core`
- `waveorder/io/core_functions.py` - Functions that work with Core objects
- `tests/mmcore_tests/test_core_func.py` - Unit tests for core functions

**Dependency declaration:**

- `pyproject.toml:68` - `"pycromanager==0.27.2"` (in optional dependencies)

### 1.2 API Usage Patterns

**Studio Object Usage (`main_widget.py:816-960`):**

- **Connection establishment**: `Studio(convert_camel_case=False)`
- **Acquisition management**: `mm.getAcquisitionManager()`
- **Acquisition settings**: `am.getAcquisitionSettings()`
- **Channel operations**: `app.getChannelExposureTime()`
- **JSON serialization**: Settings converted to/from JSON for MDA sequences

**Core Object Usage (throughout codebase):**

- **Device management**: `mmc.getAvailableConfigGroups()`,
  `mmc.getAvailableConfigs()`
- **Property control**: `mmc.setProperty()`, `mmc.getProperty()`
- **Configuration management**: `mmc.setConfig()`, `mmc.defineConfig()`
- **Image acquisition**: Direct through SnapLiveManager
- **Device queries**: `mmc.getLoadedDevices()`, `mmc.waitForDevice()`

**ZMQ Bridge Usage (`main_widget.py:834`):**

- **Bridge creation**: `zmq_bridge._bridge._Bridge()`
- **Version checking**: Direct socket communication for version validation
- **Connection management**: Low-level ZMQ socket operations

### 1.3 Key Functions in `io/core_functions.py`

**Image acquisition functions:**

- `snap_and_get_image()` - Captures images via SnapLiveManager
- `snap_and_average()` - Gets mean intensity from captured images  
- `suspend_live_sm()` - Context manager for live mode control

**Device control functions:**

- `set_lc_waves()`, `set_lc_voltage()`, `set_lc_daq()` - Liquid crystal control
- `get_lc()` - Read LC state
- `set_lc_state()` - Apply MM configuration states
- `define_config_state()` - Define MM configuration presets

## 2. pycro-manager vs pymmcore-plus Architecture

### 2.1 pycro-manager Architecture

- **ZMQ-based remote communication** with Java Micro-Manager GUI process
- **Studio object**: Wraps `org.micromanager.Studio` via JavaObject bridge
- **Core object**: Wraps `mmcorej.CMMCore` via ZMQRemoteMMCoreJ
- **mmpycorex dependency**: Provides ZMQ bridge and Core wrapper
- **Java GUI dependency**: Requires running Micro-Manager application

### 2.2 pymmcore-plus Architecture  

- **Direct Python bindings** to MMCoreAndDevices C++ library
- **CMMCorePlus class**: Extends `pymmcore.CMMCore` with enhanced functionality
- **No Java GUI requirement**: Self-contained Python implementation
- **Event system**: Built-in signaling for property changes and device events
- **MDA engine**: Pure Python acquisition engine

### 2.3 Key Architectural Differences

- **Process architecture**: Remote Java process vs. in-process Python
- **Acquisition engines**: Java MDA vs. Python MDA
- **Image data flow**: Java memory → ZMQ → Python vs. Direct C++ → Python
- **Configuration management**: Java Studio API vs. Python-native management

## 3. GUI Dependencies Analysis

### 3.1 Current Micro-Manager GUI Dependencies

**Connection requirements (from documentation):**

- Micro-Manager GUI must be running
- ZMQ server enabled on port 4827 (`Tools > Options > Run server on port 4827`)
- Specific MM version required: `20230426` nightly build

**Studio API usage for acquisitions:**

- Multi-dimensional acquisition (MDA) engine
- Acquisition manager and settings
- Channel exposure time management
- JSON-based acquisition configuration

**User workflow dependencies:**

- Initial setup requires MM GUI for device configuration
- Calibration process uses MM's configuration groups and presets
- Background acquisition uses MM's snap/live functionality

### 3.2 Impact Assessment

**Strong GUI dependencies:**

- Acquisition engine (Studio.getAcquisitionManager())
- MDA sequence execution (`runAcquisitionWithSettings()`)
- Live mode management via SnapLiveManager
- Device property browser integration

**Configuration dependencies:**

- Hardware Configuration Wizard for initial setup
- Configuration groups and presets (`State0`-`State4`)
- Device property management through GUI

**Documentation assumptions:**

- All setup guides assume running MM GUI
- Calibration procedures reference MM GUI windows
- User workflow built around GUI-first approach

## 4. Migration TODO List

### 4.1 Core API Migration

- [ ] **Replace Core import**: `from pycromanager import Core` → `from
  pymmcore_plus import CMMCorePlus`
- [ ] **Update Core instantiation**: `Core(convert_camel_case=False)` →
  `CMMCorePlus()`
- [ ] **Remove ZMQ bridge dependencies**: Remove `zmq_bridge` imports and usage
- [ ] **Update connection logic**: Replace ZMQ connection with direct MMCore
  initialization

### 4.2 Studio API Replacement

- [ ] **Remove Studio import**: Remove `from pycromanager import Studio`
- [ ] **Replace acquisition manager**: Studio-based MDA → pymmcore-plus MDA
  engine
- [ ] **Convert JSON acquisition settings**: MM SequenceSettings → useq
  MDASequence format
- [ ] **Implement acquisition functions**: Rewrite `generate_acq_settings()` and
  `acquire_from_settings()`

### 4.3 Image Acquisition Refactoring

- [ ] **Replace SnapLiveManager**: Direct MMCore image acquisition
- [ ] **Update `snap_and_get_image()`**: Use `mmc.snapImage()` +
  `mmc.getImage()`  
- [ ] **Update `snap_and_average()`**: Implement averaging in Python
- [ ] **Remove live mode suspension**: Update context manager for pymmcore-plus

### 4.4 Configuration Management

- [ ] **Update configuration group handling**: Use pymmcore-plus Configuration
  classes
- [ ] **Replace `define_config_state()`**: Use native pymmcore-plus config
  management
- [ ] **Update preset management**: Replace MM GUI preset dependencies

### 4.5 Testing and Validation  

- [ ] **Update unit tests**: Modify `test_core_func.py` for pymmcore-plus
- [ ] **Add integration tests**: Test full acquisition workflow
- [ ] **Performance benchmarking**: Compare acquisition speeds
- [ ] **Validate calibration accuracy**: Ensure LC calibration still works

### 4.6 Documentation Updates

- [ ] **Update installation guide**: Remove MM GUI requirements
- [ ] **Revise user workflow**: Self-contained Python workflow
- [ ] **Update configuration guides**: Python-based device setup
- [ ] **CLI integration**: Document standalone usage without GUI

### 4.7 Dependencies and Packaging

- [ ] **Update pyproject.toml**: Replace `pycromanager==0.27.2` with
  `pymmcore-plus`
- [ ] **Remove mmpycorex dependency**: No longer needed
- [ ] **Test optional dependencies**: Ensure `[all]` extras work correctly
- [ ] **Version compatibility**: Ensure MM device adapter compatibility

## 5. Migration Challenges and Considerations

### 5.1 Technical Challenges

**MDA Engine Compatibility:**

- Current code relies heavily on MM's Java MDA engine
- Need to translate SequenceSettings JSON to useq MDASequence
- Acquisition timing and synchronization may differ

**Image Data Handling:**

- Current ZMQ-based image transfer vs. direct memory access
- Potential performance implications (positive or negative)
- Memory management differences

**Device Driver Compatibility:**

- Ensure MMCoreAndDevices supports all required devices (Meadowlark LCs)
- Validate device property access patterns work identically

### 5.2 User Experience Impact

**Installation Simplification:**

- ✅ No need for running MM GUI
- ✅ Self-contained Python installation  
- ✅ Reduced setup complexity

**Workflow Changes:**

- ❓ Initial device configuration may need pure-Python approach
- ❓ Configuration group setup without GUI wizards
- ❓ Debugging without MM GUI device property browser

### 5.3 Migration Strategies

**Phased Approach:**

1. **Phase 1**: Replace Core object while maintaining Studio dependency
2. **Phase 2**: Implement pymmcore-plus MDA engine for acquisitions  
3. **Phase 3**: Remove all Studio dependencies and ZMQ bridge
4. **Phase 4**: Optimize and add pymmcore-plus-specific features

**Compatibility Layer:**

- Consider creating adapter functions to maintain API compatibility
- Gradual migration allowing both backends temporarily

## 6. Benefits of Migration

### 6.1 Technical Benefits

- **Simplified deployment**: No Java GUI dependency
- **Better performance**: Direct memory access vs. ZMQ serialization
- **Native Python integration**: Better error handling and debugging
- **Modern API design**: Type hints, better event system

### 6.2 User Benefits  

- **Easier installation**: Fewer dependencies and setup steps
- **Headless operation**: Suitable for automated/server deployments
- **Better reliability**: Fewer moving parts and process dependencies

### 6.3 Development Benefits

- **Easier testing**: Mock objects easier than ZMQ bridges
- **Better debugging**: Python-native stack traces
- **Future maintenance**: Single codebase vs. Java/Python coordination

## 7. Conclusion

The migration from pycro-manager to pymmcore-plus represents a significant
architectural shift that will simplify waveorder's deployment while potentially
improving performance and maintainability. The main challenges involve:

1. **Replacing the MDA acquisition engine** - This is the most complex part
2. **Removing GUI dependencies** - Requires rethinking user workflows
3. **Ensuring device compatibility** - Particularly for Meadowlark liquid
   crystals

The recommended approach is a phased migration starting with Core object
replacement, followed by MDA engine implementation, and finally removal of all
Studio dependencies. This will provide a modern, self-contained Python
microscopy control system that maintains waveorder's current functionality while
providing better deployment and maintenance characteristics.

## Summary of Key Findings

**1. Current pycro-manager Usage:**

- waveorder uses pycro-manager primarily for the `Core` and `Studio` objects
- Main usage is in `main_widget.py` for GUI operations, `acq_functions.py` for
  acquisitions, and `core_functions.py` for device control
- Heavy reliance on Java MDA acquisition engine via Studio API
- ZMQ bridge for communication with running Micro-Manager GUI

**2. Architecture Differences:**

- **pycro-manager**: Remote ZMQ connection to Java MM GUI process
- **pymmcore-plus**: Direct Python bindings to MMCoreAndDevices C++ library
- Key difference: pymmcore-plus eliminates the Java GUI dependency entirely

**3. GUI Dependencies:**

- Current workflow requires running Micro-Manager GUI with ZMQ server enabled
- Studio object heavily used for acquisition management and MDA sequences  
- Documentation and user workflows assume GUI-first approach
- However, the actual functionality (device control, image acquisition) doesn't
  inherently require the GUI

**4. Migration Challenges:**

- **Biggest challenge**: Replacing the Java MDA acquisition engine with
  pymmcore-plus's Python MDA engine
- Need to convert MM SequenceSettings JSON format to useq MDASequence format
- Image acquisition workflow needs refactoring (SnapLiveManager → direct MMCore)
- Configuration management without GUI wizards

**5. Benefits of Migration:**

- Simplified deployment (no Java GUI dependency)
- Better performance (direct memory access vs ZMQ serialization)  
- Native Python integration with better error handling
- Headless operation capability

The migration is definitely feasible and will provide significant benefits, but
requires careful planning around the MDA engine replacement and user workflow
changes. The phased approach outlined in this report would minimize risk while
achieving the migration goals.

---------------------

  Summary of Refactoring

  1. Created MM Backend Abstraction Layer (waveorder/io/mm_backend.py)

  - Abstract base class MMBackend with all necessary interface methods
  - PycromanagerBackend implementation that wraps all pycro-manager functionality
  - Global backend management functions for easy access
  - Comprehensive error handling with custom exception types

  2. Refactored Main Widget (waveorder/plugin/main_widget.py)

  - Replaced direct pycro-manager imports with backend abstraction imports
  - Simplified connect_to_mm() method to use the backend
  - Updated enter_config_group() to use the backend
  - Replaced snap_and_average() calls to use backend methods
  - Updated live mode management to use backend methods
  - Removed unused imports

  3. Refactored Acquisition Functions (waveorder/acq/acq_functions.py)

  - Updated generate_acq_settings() to accept MMBackend instead of Studio
  - Updated acquire_from_settings() to use backend instead of direct Studio calls
  - Simplified function signatures and implementations

  4. Added Comprehensive Tests (tests/mmcore_tests/test_mm_backend.py)

  - Full test coverage for the new backend abstraction
  - Mock-based tests that don't require actual MM installation
  - Tests for connection, image acquisition, settings generation, and error conditions

  Benefits of This Refactoring

  🎯 Clean Migration Path: All pycro-manager functionality is now isolated in a single module (mm_backend.py). To migrate to pymmcore-plus, you'll just need to:

  1. Create a new PymmcorePlusBackend class implementing the same MMBackend interface
  2. Switch the global backend instance
  3. No changes needed in main_widget.py or acq_functions.py

  🔧 Easy Testing: The abstraction makes it easy to create mock backends for testing without requiring a running MM instance.

  📝 Better Maintainability: All MM-specific code is centralized, making it easier to understand and modify the integration.

  🚀 Future-Proof: The interface is designed to work with both pycro-manager and pymmcore-plus, making the migration seamless.

  The repository is now ready for the pymmcore-plus migration - all pycro-manager functionality has been successfully extracted into a self-contained, easily replaceable module!
