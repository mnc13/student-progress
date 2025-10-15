import welcomeIllustration from "@/assets/well.png";
import { useAuth } from "@/contexts/AuthContext";

export function WelcomeCard() {
  const { studentId } = useAuth();

  return (
    <div className="relative bg-gradient-to-br from-[#0D6EFD] to-[#0A58CA] rounded-2xl p-8 overflow-hidden">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-0 right-0 w-96 h-96 bg-white rounded-full -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-white rounded-full translate-y/2 -translate-x-1/3" />
      </div>

      <div className="relative z-10 flex items-center justify-between">
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-white mb-3 flex items-center gap-2">
            Welcome back, Student {studentId} <span className="inline-block animate-bounce">👋</span>
          </h1>
          <p className="text-white/90 text-lg">
            You're doing <span className="font-bold">GREAT</span>!
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
