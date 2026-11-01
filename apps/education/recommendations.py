"""Explains a module test result to the learner: what to do next and why.

The pass rule itself stays in adaptive.evaluate_module_attempt (readiness >= module threshold);
this module only turns the numbers of one attempt into a recommendation stored with it.
"""

WEAK_TOPIC_LIMIT = 0.6
# Levels are measured from the module threshold in readiness points, so they keep working
# whatever threshold an administrator picks and if the readiness scale is normalised later.
LEVEL_MARGIN = 15
INDICATORS = ('theory', 'practice', 'competency')


def recommendation_level(gap):
    if gap < -LEVEL_MARGIN:
        return 'repeat'
    if gap < 0:
        return 'extra_practice'
    if gap < LEVEL_MARGIN:
        return 'next'
    return 'advanced'


def weak_topics(question_results, limit=WEAK_TOPIC_LIMIT):
    """Competencies of this attempt answered below `limit`, weakest first, with the author's spelling."""
    grouped = {}
    for question, correct in question_results:
        label = question.competency.strip()
        key = label.casefold()
        row = grouped.setdefault(key, {'competency': key, 'title': label, 'correct': 0, 'total': 0})
        row['correct'] += int(bool(correct))
        row['total'] += 1
    topics = []
    for row in grouped.values():
        row['score'] = round(row['correct'] / row['total'], 4)
        if row['score'] < limit:
            topics.append(row)
    return sorted(topics, key=lambda row: (row['score'], row['title'].casefold()))


def build_recommendation(result, question_results):
    passed = bool(result['module_passed'])
    gap = round(result['readiness'] - result['threshold'], 2)
    if passed:
        action = 'next_module' if result['next_item_short_id'] else 'course_completed'
    else:
        action = 'repeat_module'
    weakest = min(INDICATORS, key=lambda name: (result[name], INDICATORS.index(name)))
    return {
        'status': 'passed' if passed else 'repeat',
        'action': action,
        'level': recommendation_level(gap),
        'gap': gap,
        'weakest_indicator': weakest,
        'weak_topics': weak_topics(question_results),
        'weak_topic_limit': WEAK_TOPIC_LIMIT,
    }
