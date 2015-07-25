"""
Test scenarios for the crowdsource hinter xblock.
"""
import json

from django.core.urlresolvers import reverse

from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory

from courseware.tests.factories import GlobalStaffFactory
from courseware.tests.helpers import LoginEnrollmentTestCase

from lms.djangoapps.lms_xblock.runtime import quote_slashes


class TestCrowdsourceHinter(SharedModuleStoreTestCase, LoginEnrollmentTestCase):
    """
    SOLA: Please write a docstring here
    """
    STUDENTS = [
        {'email': 'view@test.com', 'password': 'foo'},
        {'email': 'view2@test.com', 'password': 'foo'}
    ]
    XBLOCK_NAMES = ['crowdsource_hinter']

    def setUp(self):
        self.course = CourseFactory.create(
            display_name='Crowdsource_Hinter_Test_Course'
        )
        self.chapter = ItemFactory.create(
            parent=self.course, display_name='Overview'
        )
        self.section = ItemFactory.create(
            parent=self.chapter, display_name='Welcome'
        )
        self.unit = ItemFactory.create(
            parent=self.section, display_name='New Unit'
        )
        self.xblock = ItemFactory.create(
            parent=self.unit,
            category='crowdsourcehinter',
            display_name='crowdsource_hinter'
        )

        self.course_url = reverse(
            'courseware_section',
            kwargs={
                'course_id': self.course.id.to_deprecated_string(),
                'chapter': 'Overview',
                'section': 'Welcome',
            }
        )

        for idx, student in enumerate(self.STUDENTS):
            username = "u{}".format(idx)
            self.create_account(username, student['email'], student['password'])
            self.activate_user(student['email'])

        self.staff_user = GlobalStaffFactory()

    def get_handler_url(self, handler, xblock_name=None):
        """
        Get url for the specified xblock handler
        """
        if xblock_name is None:
            xblock_name = TestCrowdsourceHinter.XBLOCK_NAMES[0]
        usage_key = self.course.id.make_usage_key('crowdsourcehinter', xblock_name)
        return reverse('xblock_handler', kwargs={
            'course_id': self.course.id.to_deprecated_string(),
            'usage_id': quote_slashes(usage_key.to_deprecated_string()),
            'handler': handler,
            'suffix': ''
        })

    def enroll_student(self, email, password):
        """
        Student login and enroll for the course
        """
        self.login(email, password)
        self.enroll(self.course, verify=True)

    def enroll_staff(self, staff):
        """
        Staff login and enroll for the course
        """
        email = staff.email
        password = 'test'
        self.login(email, password)
        self.enroll(self.course, verify=True)

    def call_event(self, handler, resource, xblock_name=None):
        """
        Call a ajax event (add, edit, flag, etc.) by specifying the resource
        it takes
        """
        if xblock_name is None:
            xblock_name = TestCrowdsourceHinter.XBLOCK_NAMES[0]
        url = self.get_handler_url(handler, xblock_name)
        resp = self.client.post(url, json.dumps(resource), '')
        return json.loads(resp.content)

    def check_event_response_by_element(self, handler, resource, resp_key, resp_val, xblock_name=None):
        """
        Call the event specified by the handler with the resource, and check
        whether the element (resp_key) in response is as expected (resp_val)
        """
        if xblock_name is None:
            xblock_name = TestCrowdsourceHinter.XBLOCK_NAMES[0]
        resp = self.call_event(handler, resource, xblock_name)
        self.assertEqual(resp[resp_key], resp_val)
        self.assert_request_status_code(200, self.course_url)


class TestHinterFunctions(TestCrowdsourceHinter):
    """
    Sola: Please write a docstring for this
    """
    def test_get_hint_with_no_hints(self):
        """
        Check that a generic statement is returned when no default/specific hints exist
        """
        result = self.call_event('get_hint', {'submittedanswer': 'ans=incorrect+answer+1'})
        expected = {'BestHint': 'Sorry, there are no hints for this answer.', 'StudentAnswer': 'incorrect answer 1',
                    'HintCategory': False}
        self.assertEqual(result, expected)

    def test_add_new_hint(self):
        """
        Test the ability to add a new specific hint
        """
        self.enroll_student(self.STUDENTS[0]['email'], self.STUDENTS[0]['password'])
        data = {'new_hint_submission': 'new hint for answer 1', 'answer': 'incorrect answer 1'}
        self.call_event('get_hint', {'submittedanswer': 'ans=incorrect+answer+1'})
        #result = self.call_event('add_new_hint', data)
        # SOLA: We need something here to check if the result is correct.

    def test_get_hint(self):
        """
        Check that specific hints are returned
        """
        self.call_event('get_hint', {'submittedanswer': 'ans=incorrect+answer+1'})
        submission = {'new_hint_submission': 'new hint for answer 1',
                      'answer': 'incorrect answer 1'}
        self.call_event('add_new_hint', submission)
        result = self.call_event('get_hint', {'submittedanswer': 'ans=incorrect+answer+1'})
        expected = {'BestHint': 'new hint for answer 1', 'StudentAnswer': 'incorrect answer 1',
                    'HintCategory': 'ErrorResponse'}
        self.assertEqual(result, expected)

    def test_rate_hint_upvote(self):
        """
        Test hint upvoting
        """
        self.call_event('get_hint', {'submittedanswer': 'ans=incorrect+answer+1'})
        submission = {'new_hint_submission': 'new hint for answer 1',
                      'answer': 'incorrect answer 1'}
        self.call_event('add_new_hint', submission)
        data = {
            'student_answer': 'incorrect answer 1',
            'hint': 'new hint for answer 1',
            'student_rating': 'upvote'
        }
        expected = {'success': True}
        result = self.call_event('rate_hint', data)
        self.assertEqual(result, expected)

    def test_rate_hint_downvote(self):
        """
        Test hint downvoting
        """
        self.call_event('get_hint', {'submittedanswer': 'ans=incorrect+answer+1'})
        submission = {'new_hint_submission': 'new hint for answer 1',
                      'answer': 'incorrect answer 1'}
        self.call_event('add_new_hint', submission)
        data = {
            'student_answer': 'incorrect answer 1',
            'hint': 'new hint for answer 1',
            'student_rating': 'downvote'
        }
        expected = {'success': True}
        result = self.call_event('rate_hint', data)
        self.assertEqual(result, expected)

    def test_report_hint(self):
        """
        Test hint reporting
        """
        self.call_event('get_hint', {'submittedanswer': 'ans=incorrect+answer+1'})
        submission = {'new_hint_submission': 'new hint for answer 1',
                      'answer': 'incorrect answer 1'}
        self.call_event('add_new_hint', submission)
        data = {
            'student_answer': 'incorrect answer 1',
            'hint': 'new hint for answer 1',
            'student_rating': 'report'
        }
        expected = {'rating': 'reported', 'hint': 'new hint for answer 1'}
        result = self.call_event('rate_hint', data)
        self.assertEqual(result, expected)

    def test_dont_show_reported_hint(self):
        """
        Check that reported hints are returned
        """
        self.call_event('get_hint', {'submittedanswer': 'ans=incorrect+answer+1'})
        submission = {'new_hint_submission': 'new hint for answer 1',
                      'answer': 'incorrect answer 1'}
        self.call_event('add_new_hint', submission)
        data = {
            'student_answer': 'incorrect answer 1',
            'hint': 'new hint for answer 1',
            'student_rating': 'report'
        }
        self.call_event('rate_hint', data)
        result = self.call_event('get_hint', {'submittedanswer': 'ans=incorrect+answer+1'})
        expected = {'BestHint': 'Sorry, there are no hints for this answer.', 'StudentAnswer': 'incorrect answer 1',
                    'HintCategory': False}
        self.assertEqual(result, expected)

    def test_get_used_hint_answer_data(self):
        """
        Check that hint/answer information from previous submissions are returned upon correctly
        answering the problem
        """
        self.call_event('get_hint', {'submittedanswer': 'ans=incorrect+answer+1'})
        self.call_event('get_used_hint_answer_data', "")
        submission = {'new_hint_submission': 'new hint for answer 1',
                      'answer': 'incorrect answer 1'}
        self.call_event('add_new_hint', submission)
        self.call_event('get_hint', {'submittedanswer': 'ans=incorrect+answer+1'})
        result = self.call_event('get_used_hint_answer_data', "")
        expected = {'new hint for answer 1': 'incorrect answer 1'}
        self.assertEqual(result, expected)

    def test_show_best_hint(self):
        """
        Check that the most upvoted hint is shown
        """
        self.call_event('get_hint', {'submittedanswer': 'ans=incorrect+answer+1'})
        submission1 = {'new_hint_submission': 'new hint for answer 1',
                       'answer': 'incorrect answer 1'}
        submission2 = {'new_hint_submission': 'new hint for answer 1 to report',
                       'answer': 'incorrect answer 1'}
        self.call_event('add_new_hint', submission1)
        self.call_event('add_new_hint', submission2)
        data_upvote = {
            'student_answer': 'incorrect answer 1',
            'hint': 'new hint for answer 1 to report',
            'student_rating': 'upvote'
        }
        self.call_event('rate_hint', data_upvote)
        data_downvote = {
            'student_answer': 'incorrect answer 1',
            'hint': 'new hint for answer 1 to report',
            'student_rating': 'report'
        }
        self.call_event('rate_hint', data_downvote)
        result = self.call_event('get_hint', {'submittedanswer': 'ans=incorrect+answer+1'})
        expected = {'BestHint': 'new hint for answer 1', 'StudentAnswer': 'incorrect answer 1',
                    'HintCategory': 'ErrorResponse'}
        self.assertEqual(expected, result)
