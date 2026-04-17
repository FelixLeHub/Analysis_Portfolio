;with project_status as (
select 
project_id,
project_name,
Project_budget,
'upcoming' as status
from upcoming_projects
union all
select
project_id,
Project_name,
Project_budget,
'completed' as status
from completed_projects)


-- Big table
select 
e.employee_id,
e.first_name,
e.last_name,
e.job_title,
e.salary,
d.department_name,
pa.project_id,
p.project_name,
p.status
from employees e
join departments d
on e.department_id = d.department_ID
join project_assignments pa
on pa.employee_id = e.employee_id
join project_status p
on p.project_id = pa.project_id


