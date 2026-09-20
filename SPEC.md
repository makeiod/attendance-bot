** Attendance App Spec
Purpose: 
To enable coaches to take attendance and make more fair judgements about participant effort when making selections for the funded national team. The bot should allow coaches to take attendance at the end of practice, and should minimize "cheating" on attendance when possible. The full setup (bot + database + dashboard) should enable coaches to see clear graphs and pull up data on athlete attendance, goals, and questions throughout the year, while also allowing coaches to make notes for individual athletes dated by session or undated. 
Methods:
Attendance will be taken using a discord bot, which will be integrated with the official club discord for ease of access and ease of user identification. 
Database: TBD, some verison of SQL. 
Dashboard: TBD, likely React, potentially online UCDTKD site with admin/coach login section. 
** Discord Bot
Features: 
Be able to open attendance check whenever a coach passes the command. Open a form with a questionnaire asking for feedback on the lesson/athlete performance during the lesson or a question the athlete had based on the lesson. Potentially be password gated but not necessary. Must be able to handle multiple users attemtping to log at the same time, and must ensure athlete privacy on their feedback, this should only be seen by coaches. The bot should be able to easily export or host data for coach analysis. 
