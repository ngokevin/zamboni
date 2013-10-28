# -*- coding: utf-8 -*-
from tower import ugettext_lazy as _lazy


DESC_GENERAL = _lazy(u'General Audiences')
DESC_3 = _lazy(u'Not recommended for users younger than 3 years of age')
DESC_6 = _lazy(u'Not recommended for users younger than 6 years of age')
DESC_7 = _lazy(u'Not recommended for users younger than 7 years of age')
DESC_10 = _lazy(u'Not recommended for users younger than 10 years of age')
DESC_12 = _lazy(u'Not recommended for users younger than 12 years of age')
DESC_13 = _lazy(u'Not recommended for users younger than 13 years of age')
DESC_14 = _lazy(u'Not recommended for users younger than 14 years of age')
DESC_16 = _lazy(u'Not recommended for users younger than 16 years of age')
DESC_17 = _lazy(u'Not recommended for users younger than 17 years of age')
DESC_18 = _lazy(u'Not recommended for users younger than 18 years of age')
DESC_REJECTED = _lazy(u'Rejected for All Audiences')

RATING_DESCS = {
    '0': DESC_GENERAL,
    '3': DESC_3,
    '6': DESC_6,
    '7': DESC_7,
    '10': DESC_10,
    '12': DESC_12,
    '13': DESC_13,
    '14': DESC_14,
    '16': DESC_16,
    '17': DESC_17,
    '18': DESC_18,
    'X': DESC_REJECTED,
}


class RATING(object):
    """Content rating."""


class RATING_BODY(object):
    """Content rating body."""


class CLASSIND_L(RATING):
    name = '0+'
    id = 0
    description = RATING_DESCS['0']


class CLASSIND_10(RATING):
    name = '10+'
    id = 1
    description = RATING_DESCS['10']


class CLASSIND_12(RATING):
    name = '12+'
    id = 2
    description = RATING_DESCS['12']


class CLASSIND_14(RATING):
    name = '14+'
    id = 3
    description = RATING_DESCS['14']


class CLASSIND_16(RATING):
    name = '16+'
    id = 4
    description = RATING_DESCS['16']


class CLASSIND_18(RATING):
    name = '18+'
    id = 5
    description = RATING_DESCS['18']


class CLASSIND(RATING_BODY):
    """
    The Brazilian game ratings body (aka. DEJUS, DJCTQ).
    """
    id = 0
    ratings = (CLASSIND_L, CLASSIND_10, CLASSIND_12, CLASSIND_14, CLASSIND_16,
               CLASSIND_18)
    name = 'CLASSIND'
    full_name = _lazy(u'Department of Justice, Rating, Titles and '
                      u'Qualification')
    url = ('http://portal.mj.gov.br/classificacao/data/Pages/'
           'MJ6BC270E8PTBRNN.htm')


class GENERIC_3(RATING):
    name = '3+'
    id = 0
    description = RATING_DESCS['3']


class GENERIC_7(RATING):
    name = '7+'
    id = 1
    description = RATING_DESCS['7']


class GENERIC_12(RATING):
    name = '12+'
    id = 2
    description = RATING_DESCS['12']


class GENERIC_16(RATING):
    name = '16+'
    id = 3
    description = RATING_DESCS['16']


class GENERIC_18(RATING):
    name = '18+'
    id = 4
    description = RATING_DESCS['18']


class GENERIC(RATING_BODY):
    """
    The generic game ratings body (used in Germany, for example).
    """
    id = 1
    ratings = (GENERIC_3, GENERIC_7, GENERIC_12, GENERIC_16, GENERIC_18)
    name = 'GENERIC'
    full_name = _lazy(u'Generic')


class USK_0(RATING):
    name = '0+'
    id = 0
    description = RATING_DESCS['0']


class USK_6(RATING):
    name = '6+'
    id = 1
    description = RATING_DESCS['6']


class USK_12(RATING):
    name = '12+'
    id = 2
    description = RATING_DESCS['12']


class USK_16(RATING):
    name = '16+'
    id = 3
    description = RATING_DESCS['16']


class USK_18(RATING):
    name = '18+'
    id = 4
    description = RATING_DESCS['18']


class USK_REJECTED(RATING):
    name = _lazy('Rejected')
    id = 5
    description = RATING_DESCS['X']


class USK(RATING_BODY):
    """
    The organization responsible for game ratings in Germany
    (aka. Unterhaltungssoftware Selbstkontrolle).
    """
    id = 2
    ratings = (USK_0, USK_6, USK_12, USK_16, USK_18, USK_REJECTED)
    name = 'USK'
    full_name = _lazy(u'Entertainment Software Self-Regulation Body')
    url = 'http://www.usk.de/en/'


class ESRB_E(RATING):
    """Everybody."""
    name = '0+'
    id = 0
    description = RATING_DESCS['0']


class ESRB_10(RATING):
    name = '10+'
    id = 1
    description = RATING_DESCS['10']


class ESRB_T(RATING):
    """Teen."""
    name = '13+'
    id = 2
    description = RATING_DESCS['13']


class ESRB_M(RATING):
    """Mature 17+."""
    name = '17+'
    id = 3
    description = RATING_DESCS['17']


class ESRB_A(RATING):
    """Adults Only."""
    name = '18+'
    id = 4
    description = RATING_DESCS['18']


class ESRB(RATING_BODY):
    """
    The North American game ratings body (i.e. USA, Canada).
    """
    id = 3
    ratings = (ESRB_E, ESRB_10, ESRB_T, ESRB_M, ESRB_A)
    name = 'ESRB'
    full_name = _lazy(u'Entertainment Software Rating Board')
    url = 'http://esrb.org'


class PEGI_3(RATING):
    name = '3+'
    id = 0
    description = RATING_DESCS['3']


class PEGI_10(RATING):
    name = '10+'
    id = 1
    description = RATING_DESCS['10']


class PEGI_13(RATING):
    name = '13+'
    id = 2
    description = RATING_DESCS['13']


class PEGI_18(RATING):
    name = '18+'
    id = 3
    description = RATING_DESCS['18']


class PEGI(RATING_BODY):
    """
    The European game ratings body (i.e. UK, Poland, Spain).
    """
    id = 4
    ratings = (PEGI_3, PEGI_10, PEGI_13, PEGI_18)
    name = 'PEGI'
    full_name = _lazy(u'Pan European Game Information')
    url = 'http://www.pegi.info'


RATINGS_BODIES = {
    CLASSIND.id: CLASSIND,
    GENERIC.id: GENERIC,
    USK.id: USK,
    ESRB.id: ESRB,
    PEGI.id: PEGI,
}
ALL_RATINGS = []
for rb in RATINGS_BODIES.values():
    ALL_RATINGS.extend(rb.ratings)

RATINGS_BY_NAME = []
for rb in RATINGS_BODIES.values():
    for r in rb.ratings:
        RATINGS_BY_NAME.append((ALL_RATINGS.index(r),
                                '%s - %s' % (rb.name, r.name)))
        r.ratingsbody = rb
