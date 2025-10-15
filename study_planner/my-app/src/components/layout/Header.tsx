import { Search, Sun, Moon, Bell, ChevronDown } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useState } from "react";

export function Header() {
  const [isDark, setIsDark] = useState(false);

  const toggleTheme = () => {
    setIsDark(!isDark);
    document.documentElement.classList.toggle("dark");
  };

  return (
    <header className="h-16 bg-card border-b border-border px-6 flex items-center gap-4">
      {/* Search */}
      <div className="flex-1 max-w-xl relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
        <Input
          placeholder="Search Courses, Documents, Activities..."
          className="pl-10 bg-background"
        />
      </div>

      {/* Theme Toggle */}
      <div className="flex items-center gap-1 bg-background rounded-full p-1">
        <Button
          variant="ghost"
          size="icon"
          className={`rounded-full w-8 h-8 ${!isDark ? "bg-primary text-primary-foreground" : ""}`}
          onClick={() => !isDark && toggleTheme()}
        >
          <Sun className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className={`rounded-full w-8 h-8 ${isDark ? "bg-primary text-primary-foreground" : ""}`}
          onClick={() => isDark && toggleTheme()}
        >
          <Moon className="w-4 h-4" />
        </Button>
      </div>

      {/* Notifications */}
      <Button variant="ghost" size="icon" className="relative">
        <Bell className="w-5 h-5" />
        <span className="absolute top-1 right-1 w-2 h-2 bg-destructive rounded-full" />
      </Button>

      {/* User Profile */}
      <Button variant="ghost" className="gap-2 h-10">
        <Avatar className="w-8 h-8">
          <AvatarImage src="" />
          <AvatarFallback className="bg-primary text-primary-foreground">NN</AvatarFallback>
        </Avatar>
        <span className="font-medium">Nuha Nab</span>
        <ChevronDown className="w-4 h-4" />
      </Button>
    </header>
  );
}
export default Header;