import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { FloorPlan } from '../components/monitor/FloorPlan'
import { BuildingView3D } from '../components/monitor/BuildingView3D'
import { ConnectionScreen } from '../components/ConnectionScreen'
import { AlertToasts } from '../components/AlertToasts'
import { Configuration } from '../components/admin/Configuration'
import { TagList } from '../components/monitor/TagList'
import { Analytics } from '../components/admin/Analytics'
import { ReportsView } from '../components/reports/ReportsView'
import { AdminView } from '../components/admin/AdminView'
import { CasualSetup } from '../components/admin/CasualSetup'
import { InteractiveTourGuide } from '../components/common/InteractiveTourGuide'
import { CASUAL_SETUP_TOUR, ENGINEER_STUDIO_TOUR } from '../lib/tourGuides'
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
import { CollectorCollapsible } from '../components/collector/CollectorCollapsible'
import { CollectorDropdown } from '../components/collector/CollectorDropdown'

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

    expect(screen.getByText(/System Alert: Live Hardware Endpoint Error/i)).toBeInTheDocument()
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

    fireEvent.click(screen.getByText(/Retry connection/i))
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

  it('Configuration component provides Simulation Mode toggle and Live Hardware config', () => {
    const onToggleSim = vi.fn()
    const onInterval = vi.fn()
    const onEndpoint = vi.fn()

    render(
      <Configuration
        anchors={ANCHORS}
        mode="live"
        interval={1500}
        onInterval={onInterval}
        endpoint="/api/state"
        onEndpoint={onEndpoint}
        simulationEnabled={true}
        onToggleSimulation={onToggleSim}
      />
    )

    expect(screen.getByText('Live Positioning Configuration')).toBeInTheDocument()
    expect(screen.getByText('Simulation Mode')).toBeInTheDocument()
    expect(screen.getByText('Live Hardware Data Source')).toBeInTheDocument()

    // Toggle button click
    const toggleBtn = screen.getByText('Simulated Demonstration Tag').closest('label')
    if (toggleBtn) {
      fireEvent.click(toggleBtn)
      expect(onToggleSim).toHaveBeenCalledWith(false)
    }
  })

  it('TagList renders SIMULATION badge for simulated demonstration tags', () => {
    const tagsWithSim: Tag[] = [
      {
        ...mockTag,
        id: 'SIM-01',
        label: 'Simulation Tag',
        isSimulated: true,
      },
    ]

    render(<TagList tags={tagsWithSim} selected={null} onSelect={vi.fn()} />)
    expect(screen.getByText('SIMULATION')).toBeInTheDocument()
    expect(screen.getByText('Simulation Tag')).toBeInTheDocument()
  })

  it('Analytics component renders Real Telemetry Active badge and handles real tags', () => {
    render(<Analytics sim={mockSimState} />)
    expect(screen.getByText('Real Telemetry Active')).toBeInTheDocument()
    expect(screen.getByText('System Telemetry & Spatial Analytics')).toBeInTheDocument()
  })

  it('ReportsView renders pure Activity & History audit view with subtabs', () => {
    const { container } = render(
      <ReportsView sim={mockSimState} mode="demo" />
    )

    expect(screen.getByText('Spatial Activity & History Audit')).toBeInTheDocument()
    expect(screen.getByText('Activity Overview')).toBeInTheDocument()
    expect(screen.getByText('Tag Movement History')).toBeInTheDocument()
    expect(screen.getByText('Room & Zone Occupancy')).toBeInTheDocument()
    expect(screen.getByText('Event & Alert Logs')).toBeInTheDocument()
    expect(screen.getByText('Export CSV Log')).toBeInTheDocument()
    expect(screen.getByText('Export JSON Audit')).toBeInTheDocument()

    // Switch to Tag Movement History tab
    fireEvent.click(screen.getByText('Tag Movement History'))
    expect(screen.getByText(/Trajectory History:/i)).toBeInTheDocument()
    expect(screen.getByText('Recent Position Waypoints')).toBeInTheDocument()

    // Switch to Room & Zone Occupancy tab
    fireEvent.click(screen.getByText('Room & Zone Occupancy'))
    expect(screen.getByText('Lobby')).toBeInTheDocument()

    // Switch to Event & Alert Logs tab
    fireEvent.click(screen.getByText('Event & Alert Logs'))
    expect(screen.getByText('Event & Geofence Audit Feed')).toBeInTheDocument()
  })

  it('CollectorCollapsible renders title, badge, and toggles collapse state', () => {
    const onToggle = vi.fn()
    const { getByText, queryByText } = render(
      <CollectorCollapsible
        title="Test Panel"
        badge={<span>Active Badge</span>}
        defaultOpen={true}
        onToggle={onToggle}
      >
        <div>Collapsible Child Content</div>
      </CollectorCollapsible>
    )

    expect(getByText('Test Panel')).toBeInTheDocument()
    expect(getByText('Active Badge')).toBeInTheDocument()
    expect(getByText('Collapsible Child Content')).toBeInTheDocument()

    // Click toggle header
    fireEvent.click(getByText('Test Panel'))
    expect(onToggle).toHaveBeenCalledWith(false)
    expect(queryByText('Collapsible Child Content')).not.toBeInTheDocument()

    // Click to reopen
    fireEvent.click(getByText('Test Panel'))
    expect(onToggle).toHaveBeenCalledWith(true)
    expect(getByText('Collapsible Child Content')).toBeInTheDocument()
  })

  it('CollectorDropdown renders trigger, opens menu on click, and triggers item callbacks', () => {
    const onItemClick = vi.fn()
    const { getByText, queryByText } = render(
      <CollectorDropdown
        trigger={<button type="button">Open Menu</button>}
        items={[
          { id: 'item1', label: 'Item One', onClick: onItemClick },
          {
            id: 'item2',
            label: 'Item Two With Sub',
            subItems: [
              { id: 'sub1', label: 'Sub Item One' },
            ],
          },
        ]}
      />
    )

    expect(getByText('Open Menu')).toBeInTheDocument()
    expect(queryByText('Item One')).not.toBeInTheDocument()

    // Open dropdown
    fireEvent.click(getByText('Open Menu'))
    expect(getByText('Item One')).toBeInTheDocument()
    expect(getByText('Item Two With Sub')).toBeInTheDocument()

    // Click item
    fireEvent.click(getByText('Item One'))
    expect(onItemClick).toHaveBeenCalledTimes(1)
    expect(queryByText('Item One')).not.toBeInTheDocument()
  })

  it('AdminView renders Casual Setup by default and toggles between Casual and Engineer modes', () => {
    localStorage.removeItem('rtls_setup_mode')
    const { getByText, queryByText } = render(
      <AdminView
        sim={mockSimState}
        mode="demo"
        interval={1000}
        onInterval={vi.fn()}
        endpoint="/api/state"
        onEndpoint={vi.fn()}
        mapItems={[]}
        onMapItems={vi.fn()}
        role="admin"
      />
    )

    // Verify Casual Setup is active
    expect(getByText('Casual Setup')).toBeInTheDocument()
    expect(getByText('Engineer Studio')).toBeInTheDocument()
    expect(getByText('Quick Space Setup')).toBeInTheDocument()
    expect(getByText('Step 1: Choose Your Space')).toBeInTheDocument()
    expect(queryByText('Floor Plan Designer')).not.toBeInTheDocument()

    // Switch to Engineer Mode
    fireEvent.click(getByText('Engineer Studio'))
    expect(getByText('Floor Plan Designer')).toBeInTheDocument()
    expect(getByText('Calibration')).toBeInTheDocument()
    expect(getByText('Facility & Floor Plan Studio')).toBeInTheDocument()

    // Click Calibration subtab
    fireEvent.click(getByText('Calibration'))
    expect(getByText('ML Calibration Parameters')).toBeInTheDocument()
  })

  it('CasualSetup renders friendly space presets and triggers activation', async () => {
    const onMapItems = vi.fn()
    const onNavigateToMonitor = vi.fn()

    const { getByText, getAllByText } = render(
      <CasualSetup
        mapItems={[]}
        onMapItems={onMapItems}
        onNavigateToMonitor={onNavigateToMonitor}
      />
    )

    // Check space presets
    expect(getByText('Single Studio / Office')).toBeInTheDocument()
    expect(getByText('2-Room Office Suite')).toBeInTheDocument()
    expect(getByText('4-Room Smart Complex')).toBeInTheDocument()
    expect(getByText('Open Warehouse / Hall')).toBeInTheDocument()

    // Check anchor placement options
    expect(getByText('4-Corner Coverage (Recommended)')).toBeInTheDocument()
    expect(getByText('3-Node Triangular Perimeter')).toBeInTheDocument()
    expect(getByText('Single Center Node')).toBeInTheDocument()

    // Check space environments
    expect(getByText('Open Space')).toBeInTheDocument()
    expect(getByText('Standard Office')).toBeInTheDocument()
    expect(getByText('Dense Space')).toBeInTheDocument()

    // Select 2-room office suite
    fireEvent.click(getByText('2-Room Office Suite'))

    // Click Apply & Activate Setup
    const activateButtons = getAllByText(/Activate Setup|Activate Space/i)
    fireEvent.click(activateButtons[0])

    // Verify mapItems updated and feedback shown
    expect(onMapItems).toHaveBeenCalled()
    await waitFor(() => {
      expect(getByText(/Setup applied successfully/i)).toBeInTheDocument()
    })
    expect(getByText('Open Live Monitor →')).toBeInTheDocument()

    // Click Open Live Monitor
    fireEvent.click(getByText('Open Live Monitor →'))
    expect(onNavigateToMonitor).toHaveBeenCalledTimes(1)
  })

  it('InteractiveTourGuide navigates quests, displays decision advice, and triggers completion', () => {
    window.HTMLElement.prototype.scrollIntoView = vi.fn()
    const onClose = vi.fn()
    const onTabChange = vi.fn()

    const { getByText, getByTitle, queryByText } = render(
      <InteractiveTourGuide
        steps={CASUAL_SETUP_TOUR}
        isOpen={true}
        onClose={onClose}
        onTabChange={onTabChange}
        tourTitle="Casual Setup Quest"
      />
    )

    // Verify Mission 1 content
    expect(getByText(/Quest 1: Choose Your Arena/i)).toBeInTheDocument()
    expect(getByText(/Space Sizing & Visual Room Presets/i)).toBeInTheDocument()
    expect(getByText(/MUST-HAVE/i)).toBeInTheDocument()
    expect(getByText(/What this option does:/i)).toBeInTheDocument()
    expect(getByText(/Should you use it\?/i)).toBeInTheDocument()
    expect(getByText(/Essential First Step/i)).toBeInTheDocument()
    expect(getByText(/Strategy Tip:/i)).toBeInTheDocument()

    // Advance to Mission 2
    fireEvent.click(getByText(/Next Mission/i))
    expect(getByText(/Quest 2: Deploy The Beacons/i)).toBeInTheDocument()
    expect(getByText(/Tracking Boxes Placement/i)).toBeInTheDocument()

    // Go back to Mission 1
    fireEvent.click(getByText(/Previous/i))
    expect(getByText(/Quest 1: Choose Your Arena/i)).toBeInTheDocument()

    // Advance through all 5 quests to test finish
    fireEvent.click(getByText(/Next Mission/i)) // Mission 2
    fireEvent.click(getByText(/Next Mission/i)) // Mission 3
    fireEvent.click(getByText(/Next Mission/i)) // Mission 4
    fireEvent.click(getByText(/Next Mission/i)) // Mission 5 (Last)
    expect(getByText(/Quest 5: The Grand Activation/i)).toBeInTheDocument()
    expect(getByText(/Finish Quest 🎉/i)).toBeInTheDocument()

    // Finish quest
    fireEvent.click(getByText(/Finish Quest 🎉/i))
    expect(getByText(/Quest Complete! Achievement Unlocked!/i)).toBeInTheDocument()
    expect(getByText(/Master Facility Architect/i)).toBeInTheDocument()
    expect(getByText(/↺ Replay Tour/i)).toBeInTheDocument()

    // Replay restarts
    fireEvent.click(getByText(/↺ Replay Tour/i))
    expect(getByText(/Quest 1: Choose Your Arena/i)).toBeInTheDocument()
  })

  it('AdminView launches guided quest walkthrough for both Casual and Engineer modes', () => {
    localStorage.clear()
    window.HTMLElement.prototype.scrollIntoView = vi.fn()
    const { getByText, queryByText } = render(
      <AdminView
        sim={mockSimState}
        mode="demo"
        interval={1000}
        onInterval={() => {}}
        endpoint=""
        onEndpoint={() => {}}
        mapItems={[]}
        onMapItems={() => {}}
        role="admin"
      />
    )

    // In Casual Mode by default
    expect(getByText(/Casual Quest Guide/i)).toBeInTheDocument()
    expect(queryByText(/Quest 1: Choose Your Arena/i)).not.toBeInTheDocument()

    // Open Casual Quest Guide
    fireEvent.click(getByText(/Casual Quest Guide/i))
    expect(getByText(/Quest 1: Choose Your Arena/i)).toBeInTheDocument()
    expect(getByText(/Space Sizing & Visual Room Presets/i)).toBeInTheDocument()

    // Switch to Engineer Studio
    fireEvent.click(getByText('Engineer Studio'))
    expect(getByText(/Engineer Quest Guide/i)).toBeInTheDocument()
    expect(getByText(/CAD Floor Plan Designer/i)).toBeInTheDocument()
    expect(getByText(/Log-Distance ML Calibration/i)).toBeInTheDocument()
  })
})




