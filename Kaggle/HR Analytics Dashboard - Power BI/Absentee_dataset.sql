-- Join tables
select * from Absenteeism_at_work  a
left join	compensation b
on a.ID = b.ID
left join Reasons r
on a.Reason_for_absence = r.Number


-- Find the healthiest employee
select * from Absenteeism_at_work
where Social_drinker = 0
and Social_smoker = 0
and Body_mass_index < 25
and absenteeism_time_in_hours < (select AVG(Absenteeism_time_in_hours) from Absenteeism_at_work)

-- Compensation rate increase for nonsmokers  //   budget $983,221
-- 686 nonsmokers  -->  1426880 total annual work hours --> 983221/1426880 = $0.69/hr increase to each nonsmoker pay  //  $1414.40/yr
select count(*) as nonsmokers from  Absenteeism_at_work
where Social_smoker = 0

-- Optimize query for Power Bi
select
a.ID,
r.Reason,
Month_of_absence,
Body_mass_index,
case when Body_mass_index < 18.5 then 'Underweight'
	 when Body_mass_index between 18.5 and 25 then 'Healthy Weight'
	 when Body_mass_index between 25 and 30 then 'Overweight'
	 when Body_mass_index > 30 then 'Obese'
	 else 'Unknow'
	 end as BMI_Category,
case when Month_of_absence IN (12,1,2) then 'Winter'
	 when Month_of_absence IN (3,4,5) then 'Spring'
	 when Month_of_absence IN (6,7,8) then 'Summer'
	 when Month_of_absence IN (9,10,11) then 'Fall'
	 else 'Unknown' 
	 end as Season_Names,
Seasons,
Day_of_the_week,
Transportation_expense,
Job_level,
Son,
Social_drinker,
Social_smoker,
Pet,
Disciplinary_failure,
Age,
Work_load_Average_day,
Absenteeism_time_in_hours
from Absenteeism_at_work	a -- Main table to join
left join	compensation b 
on a.ID = b.ID
left join Reasons r
on a.Reason_for_absence = r.Number
