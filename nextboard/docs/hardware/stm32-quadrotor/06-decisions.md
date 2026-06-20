# STM32 小型四旋翼无人机决策记录

**Project:** STM32 Small Quadrotor Drone
**Stage:** 06 - Decisions
**Date:** 2026-06-01

## 已决定

- 主控：STM32G431
- 架构：飞控板 + 外置 4-in-1 ESC
- 主姿态传感：SPI IMU
- 第一版不做自研三相功率级
- 第一版不做图传和云台

## 待确认

- 机架尺寸：75 mm 还是 3 寸
- 电池节数：2S 还是 3S
- 接收机协议：SBUS 还是 CRSF
- 是否加入气压计
- 是否后续接入 GPS

## 高风险项

- 飞控板布局
- 电源噪声
- PID 调参
- 首次上桨
