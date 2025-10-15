import welcomeIllustration from "@/assets/welcome-illustration.png";

export function WelcomeCard() {
  return (
    <div className="relative bg-gradient-to-br from-[#0D6EFD] to-[#0A58CA] rounded-2xl p-8 overflow-hidden">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-0 right-0 w-96 h-96 bg-white rounded-full -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-white rounded-full translate-y-1/2 -translate-x-1/3" />
      </div>

      <div className="relative z-10 flex items-center justify-between">
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-white mb-3 flex items-center gap-2">
            Welcome back, Nab <span className="inline-block animate-bounce">👋</span>
          </h1>
          <p className="text-white/90 text-lg">
            You've learned <span className="font-bold">70%</span> of your goal this week!
          </p>
          <p className="text-white/80">Keep it up and improve your progress.</p>
        </div>

        {/* Illustration */}
        <div className="hidden md:block relative w-48 h-48">
          <img 
            src={welcomeIllustration} 
            alt="Student illustration" 
            className="w-full h-full object-contain"
          />
        </div>
      </div>
    </div>
  );
}
