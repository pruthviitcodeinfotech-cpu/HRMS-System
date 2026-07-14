export const Logo = () => {
  return (
    <div className="flex items-center space-x-2 select-none">
      {/* Icon Badge */}
      <div className="h-10 w-10 rounded-xl bg-[#0B85C9] flex items-center justify-center shadow-sm shrink-0">
        <svg
          className="h-6 w-6 text-white"
          fill="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Badge Outline and user silhouette */}
          <path d="M6 14c0-1.6 1.8-3 4-3h4c2.2 0 4 1.4 4 3v1H6v-1Zm6-4a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4Z" />
          {/* Card badge lines on the right */}
          <rect x="18" y="8" width="3" height="1.5" rx="0.5" />
          <rect x="18" y="11" width="3" height="1.5" rx="0.5" />
        </svg>
      </div>

      {/* Text block */}
      <div className="flex flex-col text-left">
        <span className="text-[9px] tracking-widest text-[#556987] font-semibold uppercase leading-none">
          PETPOOJA
        </span>
        <span className="text-lg font-black tracking-tight text-slate-800 leading-tight">
          PAYROLL
        </span>
      </div>
    </div>
  );
};
