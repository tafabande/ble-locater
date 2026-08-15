import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FloorPlan } from '../components/monitor/FloorPlan'
import { BuildingView3D } from '../components/monitor/BuildingView3D'
import { ConnectionScreen } from '../components/ConnectionScreen'
import { AlertToasts } from '../components/AlertToasts'
import App from '../App'
import { ANCHORS, DEFAULT_MAP, GEOFENCES, type SimState, type Tag } from '../lib/simulation'

const mockTag: Tag = {
  id: '0xTEST',
  label: 'Test Tag',
  zone: 'Lobby',
  x: 20,
  y: 20,
  floor: 0,
  battery: 95,
  status: 'online',
  lastSeen: 100,
  nearest: 'N1',
  uncertainty: 0.5,
  readings: [
    { anchorId: 'N1', rssi: -60, distance: 2.0, used: true },
    { anchorId: 'N2', rssi: -68, distance: 3.5, used: true },
    { anchorId: 'NON_EXISTENT_ANCHOR', rssi: -75, distance: 5.0, used: true }, // Edge case: unknown anchor ID
  ],
  trail: [{ x: 20, y: 20 }],
  rssiHistory: [-60, -62, -59],
  violating: null,
}

const mockSimState: SimState = {
  anchors: ANCHORS,
  tags: [mockTag],
  geofences: GEOFENCES,
  events: [],
  alerts: [],
  pipeline: [],
  seenSeries: [],
  packetsPerSec: 10,
  startedAt: Date.now(),
}

import { ErrorDiagnosticBanner } from '../components/ErrorDiagnosticBanner'

describe('Frontend Component Tests & Error Resilience', () => {
  it('ErrorDiagnosticBanner renders loud error diagnostic details when errors occur', () => {
    const onRetry = vi.fn()
    const onSwitchDemo = vi.fn()

    render(
      <ErrorDiagnosticBanner
        mode="live"
        connStatus="error"
        error="Connection Refused: Cannot reach http://localhost:8000/api/state."
        endpoint="http://localhost:8000/api/state"
        sim={mockSimState}
        onRetry={onRetry}
        onSwitchDemo={onSwitchDemo}
      />
    )

    expect(screen.getByText('Loud Alert: Live Hardware Endpoint Error')).toBeInTheDocument()
    expect(screen.getByText('Connection Refused: Cannot reach http://localhost:8000/api/state.')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Show Diagnostics ▼'))
    expect(screen.getByText('MODE & STATUS')).toBeInTheDocument()
  })

  it('FloorPlan renders safely without crashing even when a tag references an unmapped anchor', () => {
    const onSelect = vi.fn()
    const onFocus = vi.fn()

    const { container } = render(
      <FloorPlan
        sim={mockSimState}
        mapItems={DEFAULT_MAP}
        floor={0}
        selected="0xTEST"
        onSelect={onSelect}
        focus={null}
        onFocus={onFocus}
      />
    )

    expect(container.querySelector('svg')).toBeInTheDocument()
    expect(screen.getByText('TAG-0xTEST')).toBeInTheDocument()
  })

  it('BuildingView3D renders isometric 3D view and handles interaction', () => {
    const onSelect = vi.fn()

    const { container } = render(
      <BuildingView3D
        sim={mockSimState}
        mapItems={DEFAULT_MAP}
        activeFloor={0}
        selected={null}
        onSelect={onSelect}
        focus={null}
      />
    )

    expect(container.querySelector('svg')).toBeInTheDocument()
    expect(screen.getByText('drag orbit · scroll zoom · shift-drag pan')).toBeInTheDocument()
  })

  it('ConnectionScreen renders error state and fires callback buttons', () => {
    const onRetry = vi.fn()
    const onDemo = vi.fn()

    render(
      <ConnectionScreen
        status="error"
        endpoint="http://localhost:8000/api/state"
        error="HTTP 500 Internal Error"
        onRetry={onRetry}
        onDemo={onDemo}
      />
    )

    expect(screen.getByText('No live data source')).toBeInTheDocument()
    expect(screen.getByText('HTTP 500 Internal Error')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Retry connection'))
    expect(onRetry).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByText('Switch to Simulation'))
    expect(onDemo).toHaveBeenCalledTimes(1)
  })

  it('AlertToasts renders and allows dismissing alerts', () => {
    const alerts = [
      {
        id: 'a1',
        ts: Date.now(),
        severity: 'critical' as const,
        kind: 'geofence' as const,
        tag: 'TAG-0xTEST',
        message: 'Geofence breach detected',
        acknowledged: false,
      },
    ]

    render(<AlertToasts alerts={alerts} trigger={1} />)

    expect(screen.getByText('Geofence breach detected')).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Dismiss'))
    expect(screen.queryByText('Geofence breach detected')).not.toBeInTheDocument()
  })

  it('App mounts without error and renders primary navigation shell', () => {
    render(<App />)
    expect(screen.getByText('Indoor Positioning')).toBeInTheDocument()
    expect(screen.getAllByText('FleetView')[0]).toBeInTheDocument()
  })
})
