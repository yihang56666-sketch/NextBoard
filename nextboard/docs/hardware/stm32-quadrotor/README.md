# STM32 小型四旋翼无人机项目包

**Project:** STM32 Small Quadrotor Drone
**Status:** 方案阶段
**Date:** 2026-06-01

## 这是什么

这是一个基于 STM32 的小型四旋翼无人机硬件方案包，目标是先做出能实验、能调、能悬停的原型机。

## 当前内容

- `01-requirements.md`
- `02-architecture.md`
- `03-components.md`
- `04-constraints.md`
- `05-validation.md`
- `06-decisions.md`
- `07-schematics.md`
- `hardware-solution.md`
- `plan.md`

## 当前结论

- 主控推荐 STM32G431
- 姿态传感推荐 SPI IMU
- 第一版用外置 4-in-1 ESC
- 第一版不做自研电调

## 下一步

1. 确认机架尺寸
2. 确认电池规格
3. 进入原理图引脚级设计
4. 再做 PCB 和 BOM
