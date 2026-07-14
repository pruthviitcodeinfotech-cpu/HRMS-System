export const LoginIllustration = () => {
  return (
    <div className="relative flex justify-center items-center w-full max-w-[420px] mx-auto select-none animate-in fade-in duration-700">
      <svg
        viewBox="0 0 400 360"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-auto drop-shadow-lg"
      >
        {/* Grey shadow backdrop circle */}
        <circle cx="200" cy="180" r="120" fill="#E5EFFC" />

        {/* Arms and Hands */}
        {/* Left Arm holding Mug */}
        <path
          d="M260 210c10 15 25 25 35 25s15-10 10-25l-20-40"
          stroke="#3A4D62"
          strokeWidth="6"
          strokeLinecap="round"
          fill="none"
        />
        {/* Left Hand */}
        <path d="M285 170c3-5 12-5 15 0s0 15-10 15" stroke="#3A4D62" strokeWidth="6" fill="#FFF" />

        {/* Mug */}
        <rect x="290" y="150" width="30" height="40" rx="6" fill="#1E293B" />
        {/* Mug Handle */}
        <path
          d="M320 160c8 0 8 20 0 20"
          stroke="#1E293B"
          strokeWidth="5"
          strokeLinecap="round"
          fill="none"
        />

        {/* Mouse and Right Hand */}
        {/* Right Arm */}
        <path
          d="M140 210c-15 15-30 25-45 25s-15-10-10-25l15-30"
          stroke="#3A4D62"
          strokeWidth="6"
          strokeLinecap="round"
          fill="none"
        />
        {/* Right Hand resting on Mouse */}
        <path
          d="M95 180c-5-5-15-5-15 5s5 15 15 15c8 0 10-10 0-20z"
          fill="#FFF"
          stroke="#1E293B"
          strokeWidth="4"
        />
        {/* Mouse */}
        <rect x="75" y="195" width="22" height="35" rx="11" fill="#1E293B" />
        <line x1="86" y1="195" x2="86" y2="212" stroke="#475569" strokeWidth="2" />

        {/* Person Body & Face */}
        {/* Neck */}
        <path d="M190 180h20v25h-20z" fill="#FFF" stroke="#3A4D62" strokeWidth="4" />
        {/* T-Shirt */}
        <path
          d="M150 220c15-20 30-25 50-25s35 5 50 25v60H150v-60z"
          fill="#0B85C9"
          stroke="#3A4D62"
          strokeWidth="4"
        />
        {/* Neck collar cut */}
        <path d="M185 195c10 10 20 10 30 0" stroke="#3A4D62" strokeWidth="4" fill="none" />

        {/* Head */}
        <path
          d="M170 130c0-20 15-35 30-35s30 15 30 35c0 15-8 25-30 25s-30-10-30-25z"
          fill="#FFF"
          stroke="#3A4D62"
          strokeWidth="4"
        />
        {/* Ears */}
        <circle cx="167" cy="130" r="8" fill="#FFF" stroke="#3A4D62" strokeWidth="4" />
        <circle cx="233" cy="130" r="8" fill="#FFF" stroke="#3A4D62" strokeWidth="4" />

        {/* Hair - Messy cartoon hair */}
        <path
          d="M165 125c-5-10-2-25 10-30 5-15 25-25 35-15 15-15 30 0 35 15 10 5 12 20 5 30l-5-10-20-10-20 5-20-5-20 15z"
          fill="#1E293B"
          stroke="#3A4D62"
          strokeWidth="3"
        />

        {/* Face Features */}
        {/* Eyes */}
        <circle cx="188" cy="122" r="3" fill="#1E293B" />
        <circle cx="212" cy="122" r="3" fill="#1E293B" />
        {/* Eyebrows */}
        <path d="M182 115c3-2 8-2 10 0" stroke="#3A4D62" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M208 115c3-2 8-2 10 0" stroke="#3A4D62" strokeWidth="2.5" strokeLinecap="round" />
        {/* Nose */}
        <path
          d="M200 123v8l-3 2"
          stroke="#3A4D62"
          strokeWidth="3"
          strokeLinecap="round"
          fill="none"
        />
        {/* Smile */}
        <path
          d="M187 136c5 8 20 8 25 0"
          stroke="#3A4D62"
          strokeWidth="3"
          strokeLinecap="round"
          fill="none"
        />

        {/* Laptop */}
        {/* Laptop Base */}
        <path
          d="M120 280h160v10c0 10-10 15-20 15H140c-10 0-20-5-20-15v-10z"
          fill="#334155"
          stroke="#1E293B"
          strokeWidth="4"
        />
        {/* Laptop Screen */}
        <rect
          x="130"
          y="210"
          width="140"
          height="70"
          rx="8"
          fill="#0F172A"
          stroke="#1E293B"
          strokeWidth="4"
        />
        {/* Logo on Laptop (Intersecting Double Circles) */}
        <circle cx="192" cy="245" r="10" stroke="#FFF" strokeWidth="3" fill="none" />
        <circle cx="208" cy="245" r="10" stroke="#FFF" strokeWidth="3" fill="none" />
      </svg>
    </div>
  );
};
