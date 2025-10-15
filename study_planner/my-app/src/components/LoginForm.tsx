import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const LoginForm = () => {
  const [studentId, setStudentId] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Login attempted with:", studentId);
    // Add login logic here
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
            className="w-full px-0 pb-3 pt-1 bg-transparent border-0 border-b-2 border-primary rounded-none focus-visible:ring-0 focus-visible:border-primary placeholder:text-muted-foreground text-base"
          />
        </div>

        <Button
          type="submit"
          className="w-full bg-primary hover:bg-primary/90 text-white font-medium text-base py-6 rounded-md transition-all duration-200"
        >
          login
        </Button>
      </form>
    </div>
  );
};

export default LoginForm;
