declare global {
  interface Window {
    $3Dmol: {
      createViewer: (
        element: HTMLElement,
        options: Record<string, unknown>
      ) => {
        removeAllModels: () => void;
        addModel: (data: string, format: string, options?: Record<string, unknown>) => void;
        setStyle: (sel: Record<string, unknown>, style: Record<string, unknown>) => void;
        addSurface: (type: string, options: Record<string, unknown>) => void;
        zoom: (factor: number, duration?: number) => void;
        zoomTo: () => void;
        render: () => void;
        clear: () => void;
        removeAllSurfaces: () => void;
        addCylinder: (opts: Record<string, unknown>) => void;
        removeAllShapes: () => void;
        setBackgroundColor: (color: string) => void;
        spin: (axis: string | boolean) => void;
      };
    };
  }
}

export {};
