import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import LoginForm from "@/components/LoginForm";
import GeometricBackground from "@/components/GeometricBackground";

const LoginPage = () => {
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleLogin = async (studentId: string) => {
    setIsLoading(true);
    try {
      const response = await fetch("http://localhost:8000/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ student_id: parseInt(studentId, 10) }),
      });
      if (!response.ok) throw new Error("Login failed");
      const data = await response.json();
      login(data.student_id.toString());
      navigate("/");
    } catch (error) {
      alert("Login failed: " + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background relative overflow-hidden">
      <GeometricBackground />
      <div className="relative z-10 w-full max-w-md">
        <LoginForm onLogin={handleLogin} isLoading={isLoading} />
      </div>
    </div>
  );
};

export default LoginPage;
