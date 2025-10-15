# TODO: Connect New Frontend to Backend

## 1. Create LoginPage Component
- Create a new page component that combines LoginForm and GeometricBackground.
- Handle login API call to /auth/login, store student_id on success, redirect to /dashboard.

## 2. Update App.tsx Routing
- Add /login route pointing to LoginPage.
- Protect /dashboard route (redirect to /login if no student_id).
- Add / route to redirect to /login or /dashboard based on auth.

## 3. Create AuthContext
- Create AuthContext to manage student_id and selected_course globally.
- Provide login/logout functions, course selection.

## 4. Update Sidebar Component
- Fetch courses from /students/{student_id}/courses API.
- Display courses dynamically in sidebar.
- Handle course selection, update selected_course in context.

## 5. Update PerformanceChart Component
- Fetch past items from /students/{student_id}/courses/{course}/past API.
- Plot area chart using marks data (x: idx, y: mark).

## 6. Update CompletionProgress Component
- Fetch progress from /students/{student_id}/progress API (with course query).
- Display circular progress bars per topic with completion_percent.

## 7. Update CalendarWidget Component
- Fetch upcoming events from /students/{student_id}/upcoming API (with course query).
- Mark dates on calendar based on event dates, color by course or type.

## 8. Update YourPlan Component
- Fetch tasks from /students/{student_id}/tasks API (with course query).
- Display tasks item-specific, grouped by topic.
- Auto-generate plan on login/course selection if no tasks exist, call /students/{student_id}/study-plan/generate API.

## 9. Update UpcomingItems Component
- Fetch upcoming events from /students/{student_id}/upcoming API.
- Display as list with date, title, time, location, files.

## 10. Ensure Scrollability
- Add overflow-auto to components like CompletionProgress, YourPlan, UpcomingItems where needed.

## 11. Test Integration
- Test login flow, course selection, data fetching in all components.
- Handle errors, loading states.
