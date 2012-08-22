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

            var personas = $('div.persona', queue).map(function() {
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

            $(document).keyup(function(e) {
                if (!$(queue).hasClass('shortcuts')) return;
                if ($('textarea').is(':focus') && e.which != '13') return;

                // For using Enter to submit textareas.
                if (e.which == '13' && '13' in keymap) {
                    keymap['13']();
                }

                var key = String.fromCharCode(e.which).toLowerCase();
                if (!key in keymap) return;

                var action = keymap[key];
                if (action && !e.ctrlKey && !e.altKey && !e.metaKey) {
                    personaActions[action[0]](currentpersona, action[1]);
                    return false;
                }
            });

            $('textarea').keypress(function(e) {
                if (e.keyCode == 13) {
                    e.preventDefault();
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
                        // alert('Previous Page');
                    } else if (i >= personas.length) {
                        // alert('Next Page');
                    } else {
                        $(personas[i].element).scrollTo({ duration: duration, marginTop: 20 });
                    }
                }, delay);

                delete keymap['13'];
                $('.rq-dropdown').hide();
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

            var keymap = {
                'j': ['next', null],
                'k': ['prev', null],
                'a': ['approve', null],
                'r': ['reject', null],
                'd': ['duplicate', null],
                'f': ['flag', null],
                'm': ['moreinfo', null]
            };

            function setReviewed(i, text) {
                $('.status', personas[i].element).addClass('reviewed').text(text);
                if ($(queue).hasClass('advance')) {
                    gotopersona(i+1, 500);
                }
            }

            var personaActions = {
                'next': function (i) { gotopersona(i+1); },
                'prev': function (i) { gotopersona(i-1); },

                'approve': function (i) {
                    $('div.persona:eq(' + i + ') input.action').val('approve');
                    setReviewed(i, 'Approved');
                },

                'reject': function (i) {
                    // Open up dropdown of rejection reasons and set up
                    // key and click-bindings for choosing a reason. This
                    // function does not actually do the rejecting as the
                    // rejecting is only done once a reason is supplied.
                    $('.rq-dropdown:not(.reject-reason-dropdown)').hide();
                    $('div.persona:eq(' + i + ') .reject-reason-dropdown').toggle();

                    // Dynamically add key-mapping, 0 opens up another dropdown
                    // to enter a exceptional reason for rejection.
                    keymap['0'] = ['other_reject_reason', 0];
                    for (var j = 1; j <= 9; j++) {
                        keymap[j + ''] = ['reject_reason', j];
                    }

                    var reject_reason = this.reject_reason;
                    var other_reject_reason = this.other_reject_reason;
                    $('li.reject_reason').click(function(e) {
                        var rejectId = $(this).data('id');
                        if (rejectId == '0') {
                            other_reject_reason(i);
                        } else {
                            reject_reason(i, $(this).data('id'));
                        }
                    });
                },

                'other_reject_reason': function(i) {
                    $('.rq-dropdown:not(.other-reject-reason-dropdown)').hide();
                    $('div.persona:eq(' + i + ') .other-reject-reason-dropdown').toggle();
                    var textArea = $('div.persona:eq(' + i + ') .other-reject-reason-dropdown textarea').focus();

                    // Submit link/URL of the duplicate.
                    var submit = function() {
                        $('div.persona:eq(' + i + ') input.comment').val(textArea.val());
                        textArea.blur();
                        personaActions.reject_reason(i, 0);
                    };
                    keymap['13'] = submit;
                    $('.other-reject-reason-dropdown button').click(_pd(submit));
                },

                'reject_reason': function(i, reject_reason) {
                    // Given the rejection reason, does the actual rejection of
                    // the Persona.
                    $('div.persona:eq(' + i + ') input.action').val('reject');
                    $('div.persona:eq(' + i + ') input.reject_reason').val(reject_reason);
                    setReviewed(i, 'Rejected');

                    // Remove key and click-bindings now that rejection is
                    // complete.
                    for (var i = 0; i <= 9; i++) {
                        delete keymap[i + ''];
                    }
                    $('li.reject_reason').unbind('click');
                },

                'duplicate': function(i) {
                    // Open up dropdown to enter ID/URL of duplicate.
                    $('.rq-dropdown:not(.duplicate-dropdown)').hide();
                    $('div.persona:eq(' + i + ') .duplicate-dropdown').toggle();
                    var textArea = $('div.persona:eq(' + i + ') .duplicate-dropdown textarea').focus();

                    // Submit link/URL of the duplicate.
                    var submit = function() {
                        $('div.persona:eq(' + i + ') input.action').val('reject');
                        $('div.persona:eq(' + i + ') input.reject_reason').val('duplicate');
                        $('div.persona:eq(' + i + ') input.comment').val(textArea.val());
                        textArea.blur();
                        setReviewed(i, 'Duplicate');
                    };
                    keymap['13'] = submit;
                    $('.duplicate-dropdown button').click(_pd(submit));
                },

                'moreinfo': function(i) {
                    // Open up dropdown to enter ID/URL of moreinfo.
                    $('.rq-dropdown:not(.moreinfo-dropdown)').hide();
                    $('div.persona:eq(' + i + ') .moreinfo-dropdown').toggle();
                    var textArea = $('div.persona:eq(' + i + ') .moreinfo-dropdown textarea').focus();

                    // Submit link/URL of the moreinfo.
                    var submit = function() {
                        $('div.persona:eq(' + i + ') input.action').val('moreinfo');
                        $('div.persona:eq(' + i + ') input.comment').val(textArea.val());
                        textArea.blur();
                        setReviewed(i, 'Requested Info');
                    };
                    keymap['13'] = submit;
                    $('.moreinfo-dropdown button').click(_pd(submit));
                }
            };

            $('button.approve', this).click(_pd(function(e) {
                personaActions.approve(getpersonaParent(e.currentTarget));
            }));
            $('button.reject', this).click(_pd(function(e) {
                personaActions.reject(getpersonaParent(e.currentTarget));
            }));
            $('button.duplicate', this).click(_pd(function(e) {
                e.preventDefault(); // _pd wasn't working...
                personaActions.duplicate(getpersonaParent(e.currentTarget));
            }));
            $('button.moreinfo', this).click(_pd(function(e) {
                personaActions.moreinfo(getpersonaParent(e.currentTarget));
            }));

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
