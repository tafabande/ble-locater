# Indoor Positioning Dashboard

React 19 + Vite 8 + Tailwind CSS v4 standalone operations dashboard.

## Development Server

The Vite development server runs on `http://127.0.0.1:3000` (configured via `control.py` / `launch.bat` or `npm run dev`).

- Standalone: Fully localized, 100% offline-compatible, no external cloud dependencies.
- Hot reload: Changes to source files are reflected immediately.

## Project Structure

- `src/main.tsx` - React entrypoint; imports `src/index.css` and mounts `src/App.tsx` into the `#root` element
- `src/App.tsx` - Primary application component and the root view shell
- `src/index.css` - Global CSS entrypoint and Tailwind CSS v4 theme definitions
- `index.html` - Standalone HTML5 shell containing the `#root` element
- `package.json` - Project dependencies and scripts
- `vite.config.ts` - Local Vite configuration with React, Tailwind CSS v4, and `@` alias for `src`
- `control.py` - Desktop Operations Console for hosting backend engine, simulator, and dashboard

## Dependencies

- Runtime: React 19 and React DOM 19
- Styling: Tailwind CSS v4 with `@tailwindcss/vite` plugin
- Build tooling: Vite 8, TypeScript 5.7, and `@vitejs/plugin-react`
- Testing: Vitest & React Testing Library
- Backend: Python 3 FastAPI / WebSocket engine in `ble-indoor-positioning/`
