import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { WelcomeCard } from "@/components/dashboard/WelcomeCard";
import { PerformanceChart } from "@/components/dashboard/PerformanceChart";
import { CompletionProgress } from "@/components/dashboard/CompletionProgress";
import { CalendarWidget } from "@/components/dashboard/CalendarWidget";
import { UpcomingItems } from "@/components/dashboard/UpcomingItems";
import { YourPlan } from "@/components/dashboard/YourPlan";

export default function Dashboard() {
  return (
    <div className="flex min-h-screen w-full bg-background">
      <Sidebar />
      
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        
        <main className="flex-1 p-6 overflow-auto">
          <div className="max-w-7xl mx-auto space-y-6">
            {/* Welcome Card */}
            <WelcomeCard />

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column - Charts and Plan */}
              <div className="lg:col-span-2 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <PerformanceChart />
                  <CompletionProgress />
                </div>
                <YourPlan />
              </div>

              {/* Right Column - Calendar and Upcoming */}
              <div className="space-y-6">
                <CalendarWidget />
                <UpcomingItems />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
