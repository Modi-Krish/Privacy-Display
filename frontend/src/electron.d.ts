interface Window {
  electronAPI?: {
    platform: string
    setContentProtection: (enable: boolean) => void
    setSkipTaskbar: (skip: boolean) => void
    minimizeWindow: () => void
    maximizeWindow: () => void
    closeWindow: () => void

    // Browser tab management
    createTab: (id: string, url: string) => void
    switchTab: (id: string) => void
    closeTab: (id: string) => void
    resizeBrowser: (bounds: { x: number, y: number, width: number, height: number }) => void
    navigate: (id: string, url: string) => void
    goBack: (id: string) => void
    goForward: (id: string) => void
    reload: (id: string) => void
    onBrowserNavigate: (callback: (id: string, url: string) => void) => void
    onBrowserTitleUpdated: (callback: (id: string, title: string) => void) => void

    // Overlay
    toggleOverlayClickThrough: () => void
    onOverlayModeChanged: (callback: (isClickThrough: boolean) => void) => void
  }
}

// Augment the React JSX namespace to support Electron's webview element
declare namespace JSX {
  interface IntrinsicElements {
    webview: React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement> & {
      src?: string;
      style?: React.CSSProperties;
      ref?: React.RefObject<any>;
      allowpopups?: string;
      useragent?: string;
      preload?: string;
    }, HTMLElement>;
  }
}
