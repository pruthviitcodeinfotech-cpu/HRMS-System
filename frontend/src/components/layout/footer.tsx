export const Footer = () => {
  const year = new Date().getFullYear();

  return (
    <footer className="h-12 border-t border-border bg-card/50 flex items-center justify-between px-6 text-[10px] text-muted-foreground shrink-0">
      <div>&copy; {year} HRMS Admin Portal. All rights reserved.</div>
      <div className="flex items-center space-x-4">
        <a href="#" className="hover:text-foreground transition-colors">
          Privacy Policy
        </a>
        <a href="#" className="hover:text-foreground transition-colors">
          Terms of Service
        </a>
      </div>
    </footer>
  );
};
