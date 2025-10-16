import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface LoginFormProps {
  onLogin: (studentId: string) => void;
  isLoading: boolean;
}

const LoginForm = ({ onLogin, isLoading }: LoginFormProps) => {
  const [studentId, setStudentId] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (studentId.trim()) {
      onLogin(studentId.trim());
    }
  };

  return (
    <div className="w-full max-w-md mx-auto px-6">
      <div className="mb-12 text-center">
        <h1 className="text-5xl md:text-6xl font-bold text-primary lowercase tracking-tight">
          login
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        <div className="relative">
          <Input
            type="text"
            placeholder="Student ID"
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
            disabled={isLoading}
            className="w-full px-0 pb-3 pt-1 bg-transparent border-0 border-b-2 border-primary rounded-none focus-visible:ring-0 focus-visible:border-primary placeholder:text-muted-foreground text-base"
          />
        </div>

        <Button
          type="submit"
          disabled={isLoading || !studentId.trim()}
          className="w-full bg-primary hover:bg-primary/90 text-white font-medium text-base py-6 rounded-md transition-all duration-200"
        >
          {isLoading ? "Logging in..." : "login"}
        </Button>
      </form>
    </div>
  );
};

export default LoginForm;
