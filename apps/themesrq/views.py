import jingo


def themesrq(request):
    return jingo.render(request, 'themesrq/index.html', {})
