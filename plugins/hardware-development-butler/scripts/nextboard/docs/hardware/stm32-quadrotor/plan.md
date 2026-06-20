# STM32 Quadrotor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small STM32-based quadcopter hardware package that is realistic to prototype and iterate.

**Architecture:** Use a split control/power architecture: STM32G431 flight controller, SPI IMU, optional barometer, external 4-in-1 ESC, and a 2S/3S battery. Keep the first version focused on stable attitude control, protection logic, and PCB/layout discipline.

**Tech Stack:** STM32G4, SPI IMU, UART logging, SWD debug, external ESC, KiCad/JLCPCB workflow

---

### Task 1: Freeze requirements

**Files:**
- Create: `docs/hardware/01-requirements.md`
- Modify: `docs/hardware/hardware-solution.md`

- [ ] **Step 1: Review the target use case**

```text
Small experimental quadrotor, 75 mm to 3 inch class, STM32 flight controller, external ESC, no custom power stage in v1.
```

- [ ] **Step 2: Record non-goals**

```text
No custom ESC, no vision stack, no gimbal, no GPS in v1.
```

- [ ] **Step 3: Verify the requirements file exists**

Run: `Get-ChildItem docs\hardware\01-requirements.md`
Expected: file listed

### Task 2: Lock architecture

**Files:**
- Create: `docs/hardware/02-architecture.md`

- [ ] **Step 1: Choose the flight-control architecture**

```text
STM32G431 + SPI IMU + external 4-in-1 ESC + 2S/3S battery.
```

- [ ] **Step 2: Document the fallback architecture**

```text
STM32F405/F411 can serve as a fallback if G4 parts are unavailable.
```

- [ ] **Step 3: Verify the architecture file exists**

Run: `Get-ChildItem docs\hardware\02-architecture.md`
Expected: file listed

### Task 3: Select components

**Files:**
- Create: `docs/hardware/03-components.md`

- [ ] **Step 1: Record the primary MCU and sensors**

```text
MCU: STM32G431
IMU: ICM-42688-P
Optional barometer: BMP390
```

- [ ] **Step 2: Record the power and execution chain**

```text
Battery -> protection -> 5V -> 3.3V -> MCU and sensors; 4 motors via external ESC.
```

- [ ] **Step 3: Verify the components file exists**

Run: `Get-ChildItem docs\hardware\03-components.md`
Expected: file listed

### Task 4: Define board constraints

**Files:**
- Create: `docs/hardware/04-constraints.md`

- [ ] **Step 1: Write the signal and power rules**

```text
SPI for IMU, SWD required, UART required, keep motor current out of control ground.
```

- [ ] **Step 2: Add routing guidance**

```text
Center the IMU, keep it away from switching nodes, prefer a 4-layer board.
```

- [ ] **Step 3: Verify the constraints file exists**

Run: `Get-ChildItem docs\hardware\04-constraints.md`
Expected: file listed

### Task 5: Create validation plan

**Files:**
- Create: `docs/hardware/05-validation.md`

- [ ] **Step 1: Define bring-up tests**

```text
Power, SWD, IMU readout, UART logging, receiver input.
```

- [ ] **Step 2: Define flight tests**

```text
Motor direction, mixing, no-prop attitude response, short hover.
```

- [ ] **Step 3: Verify the validation file exists**

Run: `Get-ChildItem docs\hardware\05-validation.md`
Expected: file listed

### Task 6: Capture decisions and schematic map

**Files:**
- Create: `docs/hardware/06-decisions.md`
- Create: `docs/hardware/07-schematics.md`

- [ ] **Step 1: Freeze the current design decisions**

```text
MCU fixed to STM32G431; no custom ESC in v1.
```

- [ ] **Step 2: Map the major nets**

```text
SPI -> IMU, UART -> debug and receiver, TIM outputs -> ESC, SWD -> debug.
```

- [ ] **Step 3: Verify both files exist**

Run: `Get-ChildItem docs\hardware\06-decisions.md, docs\hardware\07-schematics.md`
Expected: both files listed

### Task 7: Merge into one deliverable

**Files:**
- Create: `docs/hardware/hardware-solution.md`

- [ ] **Step 1: Summarize the buildable version**

```text
Short, realistic quadcopter package with clear next steps.
```

- [ ] **Step 2: Verify the summary exists**

Run: `Get-ChildItem docs\hardware\hardware-solution.md`
Expected: file listed
