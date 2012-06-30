from django.utils.http import urlquote

from jingo import register
import jinja2

from access import acl


@register.function
@jinja2.contextfunction
def check_contrib_stats_perms(context, addon):
    request = context['request']
    if addon.has_author(request.amo_user) or acl.action_allowed(request,
        'RevenueStats', 'View'):
        return True


@register.function
@jinja2.contextfunction
def stats_url(context, action, breakdown=None):
    addon = context['addon']
    if breakdown:
        action = '%s_%s' % (breakdown, action)
    if 'inapp' in context:
        action += '_inapp'
    return addon.get_stats_url(action=action)


@register.function
def url_quote(url):
    return urlquote(url)
