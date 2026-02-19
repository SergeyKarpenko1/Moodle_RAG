# Activity completion settings

## Activity settings
Depending on the type of activity, there are different completion requirements. For example, a Page might have the requirement to _require view_ ; a Quiz might have the requirement to _require grade_ while a Forum might have the requirement to _require posts/discussions/replies_.

[New feature
in **Moodle 4.3**!](https://docs.moodle.org/403/en/Category:New_features "Category:New features")

The completion requirements display progressively depending on what the teacher selects and what the default completion settings defined by the admin are.
For example, in this assignment the default setting is _None_ :
When the teacher selects _Add requirements_ , it opens up more options:
When the teacher selects _Receive a grade_ it opens up more options, e.g. Pass grade:

### View the activity
When this option is ticked, students have to view the activity i.e. click the link in order to complete it. No need to check the 'view' condition if you have other requirements.
### Require grade
When this option is ticked, students have to get a grade on the activity in order to complete it. For example, a quiz would be marked completed as soon as the user submits it (so long as it doesn't contain any "essay" questions).
It does not matter how well the student did. Getting any grade will mark the activity completed.
### Receive a passing grade
A passing grade may be required for completion of a graded activity. This condition is used together with the Require grade requirement.
### Quiz completion settings
#### Setting a grade to pass for a quiz
It is possible to distinguish between 'pass' and 'fail' grades so that a quiz becomes 'completed, passed' or 'completed, not passed' instead of just 'completed'. These results show a different icon and alternative text in the Activity completion report.
To set this up, you need to specify the pass value for the quiz activity's individual grade:
  1. Go to the Quiz settings and in the Grade section, locate the 'Grade to pass' field.
  2. Enter a grade value (e.g. 5.0)
  3. Click the 'Save changes' button

'Completed, passed' shows a green tick and 'Completed, not passed' shows a red cross.
Once you have done this, anybody submitting the quiz will receive either the pass or fail completion icon. If the quiz can be taken multiple times, the completion icon will automatically update whenever the grade does.
There is one limitation: this only works if grades are immediately visible to students. The grade must be neither permanently hidden, nor hidden until a certain date. If a grade is hidden then only the standard 'completed' state will be displayed - even once the hidden date has passed.
#### Require passing grade
If a grade to pass is set for the quiz then it will be marked complete once the student obtains this grade.
If a certain number of attempts are allowed, the quiz may be marked complete once the student has done them all (even if, for example, they did not achieve the passing grade.)
Note that _Require grade_ must be ticked as well as "Require passing grade".
#### Require attempts in a quiz
Quizzes may be automatically marked complete when one or more attempts have been submitted. This can be helpful for example when manually graded questions are included but the teacher wants the quiz to be complete before these questions are graded.
### Lesson completion settings
The following settings are specific to the Lesson activity (in addition to the standard ones)
#### Require end reached
In order for the lesson to be marked complete, the student must go to the very last page of the lesson.
#### Require time spent
In order for the lesson to be marked complete, the student must stay within the lesson pages for the time specified by the teacher here. The time can range from seconds to weeks. If they finish the lesson sooner, they will see an alert saying they did not reach the minimum time acceptable and may have to repeat the lesson.
[](https://docs.moodle.org/403/en/File:lessonstudentviewrequiretimespent.png)Student message if the condition is not met.
### Assignment completion settings
##### Student must submit to this activity to complete it
This setting means that an assignment may be considered as completed once the student has submitted it but before the teacher has had time to grade it.
### Forum completion settings
#### Require posts
For the forum to be classed as "complete" the student must either start a discussion or reply to a discussion. The total number of posts they must make can be specified in the box.
#### Require discussions
For the forum to be classed as "complete", the student must start a discussion topic. The number of posts they must make can be specified in the box. _Note: this requirement cannot be satisfied using the "Single simple discussion" and the "Q and A" forum types, since students cannot create discussions in those two types._
#### Require replies
For the forum to be classed as "complete" the student must reply to a discussion. The number of posts they must make can be specified in the box.
### Expect completed on
When a date is entered here for an activity (e.g. Forum, Choice), or for a resource, such as a Page or Folder, the expected completion date will be displayed in the Timeline block.
## Locked completion options
If at least one person has completed an activity, completion options are 'locked'. This is because changing these options may result in unexpected behaviour. For example, if somebody has ticked an activity as manually completed, and you then set it to automatic completion, the activity will become unticked - very confusing for the student who had already ticked it!       _Tip:_ It is best not to unlock options unless you are sure it won't cause problems - for example, if you know that students don't have access to the course yet, so it will only be staff who have marked the activity completed when testing.
## What happens when you unlock
Once you unlock options and then click 'Save changes', all completion information for the activity will be deleted then recalculated where possible. Manual completion can't be recalculated, so in this case the student will need to mark it as done again.
If you change completion options while a student is logged in, they may not see the changes for some minutes.
## Required course settings
Completion tracking in a course may be disabled/enabled and shown/hidden from the actions menu >Edit settings (Boost theme) or via the course administration block (Classic theme). Completion tracking may be set to show or hide conditions on the course page. Manual completion for Label, URL and File will still display the 'Mark as done' button even when completion conditions are hidden.
All activity completion conditions are now also visible when clicking into an activity, even when the completion conditions are hidden on the course page.
Manual completion may now be done from within the activity, meaning learners can move directly from one activity to the next, without going back to the main course page.
## Site administration settings
Completion tracking is enabled by default from _Site administration > General > Advanced features,_ but can be disabled here if not wanted on the site.
[New feature
in **Moodle 4.3**!](https://docs.moodle.org/403/en/Category:New_features "Category:New features")
Site level default completion settings
From _Site administration > Courses > Default settings_, a new page Default activity completion allows admins to specify sensible default completion for settings in new courses, making it easier for teachers to manage activity completion. All activities are set to None if the admin makes no changes.
## Course activity default settings
Within a course, the default settings for activity completion may be changed and several activities may have their completion settings updated at once, from _Course navigation > More > Course completion_ and selecting either Default activity completion or Bulk edit activity completion.

**Default activity completion** is the same page as the site-level default activity completion page and allows teachers to change the site-level defaults for their course.
**Bulk edit activity completion** allows you to change the completion requirements of one or several existing activities in one step. For example, if you have four quizzes with manual activity completion, you can bulk edit them so that all four require a grade to be marked complete.
## Capabilities
  * Be shown on completion reports
  * Override activity completion status
  * View activity completion reports
  * Manually mark activities as complete

## Sources
- [Activity completion settings](https://docs.moodle.org/403/en/Activity_completion_settings)

## Media
### Images
- https://docs.moodle.org/403/en/images_en/2/25/43pass.jpg
- https://docs.moodle.org/403/en/images_en/4/41/sitedefault.jpg
- https://docs.moodle.org/403/en/images_en/7/72/quizpassfail.png
- https://docs.moodle.org/403/en/images_en/c/c2/43none.jpg
- https://docs.moodle.org/403/en/images_en/e/e1/43addreq.jpg
- https://docs.moodle.org/403/en/images_en/thumb/2/25/43pass.jpg/600px-43pass.jpg
- https://docs.moodle.org/403/en/images_en/thumb/3/3d/lessonstudentviewrequiretimespent.png/300px-lessonstudentviewrequiretimespent.png
- https://docs.moodle.org/403/en/images_en/thumb/3/3d/lessonstudentviewrequiretimespent.png/450px-lessonstudentviewrequiretimespent.png
- https://docs.moodle.org/403/en/images_en/thumb/3/3d/lessonstudentviewrequiretimespent.png/600px-lessonstudentviewrequiretimespent.png
- https://docs.moodle.org/403/en/images_en/thumb/7/72/quizpassfail.png/400px-quizpassfail.png
- https://docs.moodle.org/403/en/images_en/thumb/c/c2/43none.jpg/600px-43none.jpg
- https://docs.moodle.org/403/en/images_en/thumb/d/de/newlessonconditions.png/1200px-newlessonconditions.png
- https://docs.moodle.org/403/en/images_en/thumb/d/de/newlessonconditions.png/600px-newlessonconditions.png
- https://docs.moodle.org/403/en/images_en/thumb/d/de/newlessonconditions.png/900px-newlessonconditions.png
- https://docs.moodle.org/403/en/images_en/thumb/e/e1/43addreq.jpg/600px-43addreq.jpg
