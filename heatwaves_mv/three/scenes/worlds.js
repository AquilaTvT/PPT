// Colour worlds for MV-B (ink sets). Every scene reads its inks from here so a section can swap worlds.
export const WORLDS = {
  night: {
    skyTop: '#141A33', skyHor: '#2C4C9A', skyBand: '#3F5F8F', fog: '#1E2550', stars: 1.0,
    road: '#26345E', roadShade: '#141A33', line: '#EDE3CF', wall: '#3F5F8F', wallShade: '#1E2550',
    sea: '#1E2550', seaHi: '#C9D3DC', house: '#26345E', houseShade: '#141A33', roof: '#1A1416',
    window: '#F0B45A', lamp: '#F5D08A', glow: '#F08A3C', pole: '#1A1416', mirrorPole: '#F08A3C',
    mirror: '#C9D3DC', vend: '#EDE3CF', vendGlow: '#7FC8B8', led: '#7FC8B8', moon: '#EDE3CF', moonShade: '#C9B98F',
    rail: '#C9D3DC', ballast: '#1E2550', ink: '#141018', light: [0.3, 0.75, -0.6], ambient: 0.32,
  },
  noon: {
    skyTop: '#2D6BE0', skyHor: '#C9E2F5', skyBand: '#F5F1E6', fog: '#C9E2F5', stars: 0.0,
    road: '#8E95A6', roadShade: '#4A5878', line: '#F5F1E6', wall: '#E6E0D2', wallShade: '#8E95A6',
    sea: '#2C4C9A', seaHi: '#F5F1E6', house: '#E6E0D2', houseShade: '#8E95A6', roof: '#2C4C9A',
    window: '#2C4C9A', lamp: '#E6E0D2', glow: '#F5C842', pole: '#3A3236', mirrorPole: '#F08A3C',
    mirror: '#C9D3DC', vend: '#D9402B', vendGlow: '#F5C842', led: '#D9402B', moon: '#FFF6DC', moonShade: '#F5C842',
    rail: '#5A6070', ballast: '#8E95A6', ink: '#1A1416', light: [0.25, 0.95, 0.2], ambient: 0.55,
  },
  dusk: {
    skyTop: '#2B2350', skyHor: '#F08A3C', skyBand: '#F5C842', fog: '#7A3E5A', stars: 0.2,
    road: '#4A3558', roadShade: '#2B2350', line: '#F5D7A0', wall: '#7A3E5A', wallShade: '#2B2350',
    sea: '#4A3558', seaHi: '#F5C842', house: '#4A3558', houseShade: '#2B2350', roof: '#1A1416',
    window: '#F5C842', lamp: '#F5D08A', glow: '#F08A3C', pole: '#1A1416', mirrorPole: '#D9402B',
    mirror: '#F5D7A0', vend: '#EDE3CF', vendGlow: '#F5C842', led: '#F08A3C', moon: '#F5C842', moonShade: '#F08A3C',
    rail: '#F5D7A0', ballast: '#2B2350', ink: '#1A1416', light: [-0.5, 0.35, 0.8], ambient: 0.3,
  },
  dawn: {
    skyTop: '#3A4A8A', skyHor: '#F2A7A0', skyBand: '#F7E3C2', fog: '#8E7FA8', stars: 0.0,
    road: '#5A5E86', roadShade: '#33365E', line: '#F7E3C2', wall: '#9C95B8', wallShade: '#5A5E86',
    sea: '#5A5E86', seaHi: '#F7E3C2', house: '#5A5E86', houseShade: '#33365E', roof: '#2A2440',
    window: '#F7C98A', lamp: '#F7E3C2', glow: '#F2A7A0', pole: '#2A2440', mirrorPole: '#F08A3C',
    mirror: '#F7E3C2', vend: '#EDE3CF', vendGlow: '#7FC8B8', led: '#7FC8B8', moon: '#FFF2D6', moonShade: '#F2A7A0',
    rail: '#F7E3C2', ballast: '#33365E', ink: '#1A1630', light: [0.6, 0.25, 0.75], ambient: 0.38,
  },
};
