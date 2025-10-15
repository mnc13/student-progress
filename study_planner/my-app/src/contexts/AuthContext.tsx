import { createContext, useContext, useState, useEffect, ReactNode } from "react";

interface AuthContextType {
  studentId: string | null;
  selectedCourse: string | null;
  login: (studentId: string) => void;
  logout: () => void;
  setSelectedCourse: (course: string | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [studentId, setStudentId] = useState<string | null>(null);
  const [selectedCourse, setSelectedCourse] = useState<string | null>(null);

  useEffect(() => {
    const storedStudentId = localStorage.getItem("student_id");
    if (storedStudentId) {
      setStudentId(storedStudentId);
    }
  }, []);

  const login = (newStudentId: string) => {
    setStudentId(newStudentId);
    localStorage.setItem("student_id", newStudentId);
  };

  const logout = () => {
    setStudentId(null);
    setSelectedCourse(null);
    localStorage.removeItem("student_id");
  };

  return (
    <AuthContext.Provider value={{ studentId, selectedCourse, login, logout, setSelectedCourse }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
