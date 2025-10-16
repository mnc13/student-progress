import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Area, AreaChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
        <p className="font-medium">{`Item ${data.x}: ${data.topic}`}</p>
        <p className="text-primary">{`obtained: ${(data.value * 100).toFixed(1)}%`}</p>
      </div>
    );
  }
  return null;
};

export function PerformanceChart() {
  const { studentId, selectedCourse } = useAuth();

  const { data: pastItems, isLoading } = useQuery({
    queryKey: ["pastItems", studentId, selectedCourse],
    queryFn: () => studentId && selectedCourse ? api.getPastItems(parseInt(studentId), selectedCourse) : Promise.resolve([]),
    enabled: !!studentId && !!selectedCourse,
  });

  const chartData = pastItems ? pastItems.map((item: any) => ({
    x: item.idx,
    value: item.percent / 100,
    topic: item.topic,
  })) : [];

  return (
    <Card className="h-96 shadow-xl shadow-blue-200/60">
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Performance - {selectedCourse || "Overall"}</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex items-end justify-center pb-4">
        {isLoading ? (
          <div className="h-[200px] flex items-center justify-center text-muted-foreground">Loading...</div>
        ) : chartData.length === 0 ? (
          <div className="h-[200px] flex items-center justify-center text-muted-foreground">No data available</div>
        ) : (
          <div className="w-full h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="x"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: 'hsl(var(--muted-foreground))' }}
                />
                <YAxis
                  domain={[0, 1]}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: 'hsl(var(--muted-foreground))' }}
                  tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  fill="url(#colorValue)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
export default PerformanceChart;
