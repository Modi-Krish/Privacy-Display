interface Window {
  electronAPI?: {
    platform: string
    setContentProtection: (enable: boolean) => void
    setSkipTaskbar: (skip: boolean) => void
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
