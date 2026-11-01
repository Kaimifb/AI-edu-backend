from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase

from apps.assessments.models import TestAttempt
from .recommendations import build_recommendation, recommendation_level, weak_topics
from . import test_adaptive


def answers(*rows):
    return [(SimpleNamespace(competency=name), correct) for name, correct in rows]


def result(readiness, threshold=60, passed=None, next_item='lecture-2', theory=.5, practice=1, competency=.5):
    return {'readiness': readiness, 'threshold': threshold,
            'module_passed': readiness >= threshold if passed is None else passed,
            'next_item_short_id': next_item, 'theory': theory, 'practice': practice, 'competency': competency}


class RecommendationRulesTests(SimpleTestCase):
    def test_levels_are_measured_from_the_threshold(self):
        self.assertEqual([recommendation_level(gap) for gap in (-30, -15.01, -15, -0.01, 0, 14.99, 15, 25)],
                         ['repeat', 'repeat', 'extra_practice', 'extra_practice', 'next', 'next', 'advanced', 'advanced'])

    def test_readiness_equal_to_threshold_moves_on(self):
        recommendation = build_recommendation(result(60), [])
        self.assertEqual((recommendation['status'], recommendation['action'], recommendation['gap']),
                         ('passed', 'next_module', 0))

    def test_failure_explains_gap_and_weakest_indicator(self):
        recommendation = build_recommendation(result(31, theory=.5, practice=.4, competency=.45), [])
        self.assertEqual(recommendation['status'], 'repeat')
        self.assertEqual(recommendation['action'], 'repeat_module')
        self.assertEqual(recommendation['level'], 'repeat')
        self.assertEqual(recommendation['gap'], -29)
        self.assertEqual(recommendation['weakest_indicator'], 'practice')

    def test_last_module_completes_the_course(self):
        self.assertEqual(build_recommendation(result(90, next_item=None), [])['action'], 'course_completed')

    def test_weak_topics_are_below_sixty_percent_weakest_first(self):
        topics = weak_topics(answers(('Pandas', True), ('pandas ', False), ('Визуализация', False),
                                     ('Регрессия', True), ('Регрессия', True), ('Очистка', True), ('Очистка', False),
                                     ('Очистка', False)))
        self.assertEqual([(row['title'], row['score']) for row in topics],
                         [('Визуализация', 0), ('Очистка', .3333), ('Pandas', .5)])
        self.assertEqual((topics[2]['correct'], topics[2]['total']), (1, 2))


class RecommendationFlowTests(TestCase):
    setUp = test_adaptive.AdaptiveLearningTests.setUp
    make_lecture = test_adaptive.AdaptiveLearningTests.make_lecture
    prepare = test_adaptive.AdaptiveLearningTests.prepare
    submit = test_adaptive.AdaptiveLearningTests.submit

    def test_failed_attempt_stores_a_repeat_recommendation_with_weak_topics(self):
        self.prepare()
        recommendation = self.submit(2)['adaptive_result']['recommendation']
        self.assertEqual(recommendation['status'], 'repeat')
        self.assertEqual(recommendation['action'], 'repeat_module')
        self.assertEqual([row['title'] for row in recommendation['weak_topics']], ['application'])
        self.assertEqual(TestAttempt.objects.get().adaptive_result['recommendation'], recommendation)

    def test_passed_attempt_recommends_the_next_module(self):
        self.prepare()
        recommendation = self.submit()['adaptive_result']['recommendation']
        self.assertEqual((recommendation['status'], recommendation['action']), ('passed', 'next_module'))
        self.assertEqual(recommendation['weak_topics'], [])
        self.assertEqual(recommendation['gap'], 17)
        self.assertEqual(recommendation['level'], 'advanced')
