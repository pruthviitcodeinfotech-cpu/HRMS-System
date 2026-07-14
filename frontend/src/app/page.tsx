export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-background p-6 text-foreground font-sans">
      <div className="w-full max-w-md rounded-lg border border-border bg-card p-8 shadow-base text-center">
        <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-success/10 text-success">
          <svg
            className="h-6 w-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M5 13l4 4L19 7"
            ></path>
          </svg>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground mb-2">
          HRMS Project Initialized
        </h1>
        <p className="text-sm text-foreground/75 mb-6">
          The production-ready Next.js frontend scaffolding has been successfully built and
          configured for enterprise development.
        </p>
        <div className="space-y-3 text-left">
          <div className="flex items-center space-x-2 text-xs">
            <span className="h-2.5 w-2.5 rounded-full bg-success"></span>
            <span className="font-mono text-foreground/90">TypeScript Strict Mode: Enabled</span>
          </div>
          <div className="flex items-center space-x-2 text-xs">
            <span className="h-2.5 w-2.5 rounded-full bg-success"></span>
            <span className="font-mono text-foreground/90">App Router: Configured</span>
          </div>
          <div className="flex items-center space-x-2 text-xs">
            <span className="h-2.5 w-2.5 rounded-full bg-success"></span>
            <span className="font-mono text-foreground/90">Path Aliases (@/*): Active</span>
          </div>
          <div className="flex items-center space-x-2 text-xs">
            <span className="h-2.5 w-2.5 rounded-full bg-success"></span>
            <span className="font-mono text-foreground/90">Design Token Variables: Mapped</span>
          </div>
        </div>
      </div>
    </main>
  );
}
