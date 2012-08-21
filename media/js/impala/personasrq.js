(function($) {
    $.fn.scrollTo = function(opts) {
        if (!this.length) return this;
        opts = $.extend({
            duration: 500,
            marginTop: 0,
            complete: undefined
        }, opts || { });
        var top = this.offset().top - opts.marginTop;
        $('html, body').animate({ 'scrollTop': top }, opts.duration, undefined, opts.complete);
        return this;
    };
})(jQuery);


(function($) {
    $.fn.personaQueue = function() {
        return this.each(function() {
            var queue = this;
            var currentpersona = 0;
            var cacheQueueHeight;

            var personas = $('.persona', queue).map(function() {
                return {
                    element: this,
                    top: 0
                };
            }).get();

            $(window).scroll(function() {
                updateMetrics();
                var i = findCurrentpersona();
                if (i != currentpersona) {
                    switchpersona( findCurrentpersona() );
                }
            });

            $('.persona .choices button', this).click(function(e) {
                var i = getpersonaParent(e.currentTarget);
                personaActions.approve(i);
                return false;
            });

            $(document).keyup(function(e) {
                if (!$(queue).hasClass('shortcuts')) return;

                var key = String.fromCharCode(e.which).toLowerCase();
                var action = keymap[key];
                if (action && !e.ctrlKey && !e.altKey && !e.metaKey) {
                    personaActions[action](currentpersona);
                    return false;
                }
            });

            $('.persona', queue).removeClass('active');
            updateMetrics();
            switchpersona( findCurrentpersona() );


            function updateMetrics() {
                var queueHeight = $(queue).height();
                if (queueHeight === cacheQueueHeight) return;
                cacheQueueHeight = queueHeight;

                $.each(personas, function(i, obj) {
                    var elem = $(obj.element);
                    obj.top = elem.offset().top + elem.outerHeight()/2;
                });
            }

            function getpersonaParent(elem) {
                var parent = $(elem).closest('.persona').get(0);
                for (var i = 0; i < personas.length; i++) {
                    if (personas[i].element == parent) {
                        return i;
                    }
                }
                return -1;
            }

            function gotopersona(i, delay, duration) {
                delay = delay || 0;
                duration = duration || 250;

                setTimeout(function() {
                    if (i < 0) {
                        alert('Previous Page');
                    } else if (i >= personas.length) {
                        alert('Next Page');
                    } else {
                        $(personas[i].element).scrollTo({ duration: duration, marginTop: 20 });
                    }
                }, delay);
            }

            function switchpersona(i) {
                $(personas[currentpersona].element).removeClass('active');
                $(personas[i].element).addClass('active');
                currentpersona = i;
            }

            function findCurrentpersona() {
                var pageTop = $(window).scrollTop();

                if (pageTop <= personas[currentpersona].top) {
                    for (var i = currentpersona-1; i >= 0; i--) {
                        if (personas[i].top < pageTop) {
                            break;
                        }
                    }
                    return i+1;
                }

                else {
                    for (var i = currentpersona; i < personas.length-1; i++) {
                        if (pageTop <= personas[i].top) {
                            break;
                        }
                    }
                    return i;
                }
            }

            function setReviewed(i) {
                $('.status', personas[i].element).addClass('reviewed');
                if ($(queue).hasClass('advance')) {
                    gotopersona(i+1, 500);
                }
            }

            var personaActions = {
                'next': function (i) { gotopersona(i+1); },
                'prev': function (i) { gotopersona(i-1); },

                'approve': function (i) {
                    setReviewed(i);
                }
            };

            var keymap = {
                'j': 'next',
                'k': 'prev',
                'a': 'approve',
                'r': 'reject',
                'd': 'duplicate',
                'f': 'flag',
                'm': 'moreInfo'
            };
        });
    };

    $.fn.personaQueueOptions = function(queueSelector) {
        return this.each(function() {
            var self = this;

            $('input', self).click(onChange);
            $('select', self).change(onChange);
            onChange();

            function onChange(e) {
                var category = $('#rq-category', self).val();
                var details = true /* $('#rq-details:checked', self).val() */;
                var advance = $('#rq-advance:checked', self).val();
                var single = true /* $('#rq-single:checked', self).val() */;
                var shortcuts = true /* $('#rq-shortcuts:checked', self).val() */;

                $(queueSelector)
                    .toggleClass('details', details !== undefined)
                    .toggleClass('advance', advance !== undefined)
                    .toggleClass('single', single !== undefined)
                    .toggleClass('shortcuts', shortcuts !== undefined);

                $('.shortcuts', self).toggle(shortcuts);
            }
        });
    };
})(jQuery);


$(document).ready(function() {
    $('.zoombox').zoomBox();
    $('.persona-queue').personaQueue();
    $('.sidebar').personaQueueOptions('.persona-queue');
});
