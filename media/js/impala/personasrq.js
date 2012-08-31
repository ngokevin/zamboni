(function($) {
    /* jQuery.ScrollTo by Ariel Flesler */
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
            var maxLocks = parseInt($('.persona-queue').data('max-locks'), 10);
            var moreUrl = $('.persona-queue').data('more-url');

            var personasList = $('div.persona', queue);
            var personas = personasList.map(function() {
                return {
                    element: this,
                    top: 0
                };
            }).get();

            function nthPersona(i) {
                return personasList[i];
            }

            $(window).scroll(_.throttle(function() {
                updateMetrics();
                var i = findCurrentPersona();
                if (i >= 0 && i != currentpersona) {
                    switchPersona(findCurrentPersona());
                }
            }, 250));

            $(document).keyup(function(e) {
                if (!$(queue).hasClass('shortcuts')) return;

                // Ignore key-bindings when textarea focused.
                if (fieldFocused(e) && e.which != z.keys.ENTER) return;

                // For using Enter to submit textareas.
                if (e.which == z.keys.ENTER && z.keys.ENTER in keymap) {
                    keymap[z.keys.ENTER]();
                }

                var key = String.fromCharCode(e.which).toLowerCase();
                if (!key in keymap) return;

                var action = keymap[key];
                if (action && !e.ctrlKey && !e.altKey && !e.metaKey) {
                    personaActions[action[0]](currentpersona, action[1]);
                    return false;
                }
            });

            // Pressing Enter in text field doesn't add carriage return.
            $('textarea').keypress(function(e) {
                if (e.keyCode == z.keys.ENTER) {
                    e.preventDefault();
                }
            });

            $('.persona', queue).removeClass('active');
            updateMetrics();
            switchPersona(findCurrentPersona());

            function updateMetrics() {
                var queueHeight = $(queue).height();
                if (queueHeight === cacheQueueHeight) return;
                cacheQueueHeight = queueHeight;

                $.each(personas, function(i, obj) {
                    var elem = $(obj.element);
                    obj.top = elem.offset().top + elem.outerHeight()/2;
                });
            }

            function getPersonaParent(elem) {
                var parent = $(elem).closest('.persona').get(0);

                // Easier than $.each since loop involves returning values.
                for (var i = 0; i < personas.length; i++) {
                    if (personas[i].element == parent) {
                        return i;
                    }
                }
                return -1;
            }

            function goToPersona(i, delay, duration) {
                delay = delay || 0;
                duration = duration || 250;
                setTimeout(function() {
                    if (i >= 0 && i < personas.length) {
                        $(personas[i].element).scrollTo({ duration: duration, marginTop: 20 });
                    }
                }, delay);

                delete keymap[z.keys.ENTER];
                $('.rq-dropdown').hide();
            }

            function switchPersona(i) {
                $(personas[currentpersona].element).removeClass('active');
                $(personas[i].element).addClass('active');
                currentpersona = i;
            }

            function findCurrentPersona() {
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
                    for (var i = currentpersona; i < personas.length; i++) {
                        if (pageTop <= personas[i].top) {
                            return i;
                        }
                    }
                }
            }

            var ajaxLockFlag = 0;
            function morePersonas() {
                // Don't do anything if max locks or currently making request
                // or not all personas reviewed. Using an exposed DOM element to
                // hold data, but we don't really care if they try to tamper
                // with that.
                var personaCount = $('#total').text();
                if (personasList.length >= maxLocks || ajaxLockFlag ||
                    $('#reviewed-count').text() != personaCount) {
                    return;
                }
                ajaxLockFlag = 1;
                var i = parseInt(personaCount, 10);
                $.get(moreUrl, function(data) {
                    // Update total.
                    $('#total').text(data.count);

                    // Insert the personas into the DOM.
                    $('#persona-queue-form').append(data.html);
                    personasList = $('div.persona', queue);
                    personas = personasList.map(function() {
                        return {
                            element: this,
                            top: 0
                        };
                    }).get();

                    // Correct the new Django forms' prefixes
                    // (id_form-x-field) to play well with the formset.
                    var $input;
                    var newPersonas = personasList.slice(personaCount, personasList.length);
                    $(newPersonas).each(function(index, persona) {
                        $('input', persona).each(function(index, input) {
                            $input = $(input);
                            $input.attr('id', $input.attr('id').replace(/-\d-/, '-' + personaCount + '-'));
                            $input.attr('name', $input.attr('name').replace(/-\d-/, '-' + personaCount + '-'));
                        });
                        personaCount++;
                    });

                    // Update metadata on Django management form for
                    // formset.
                    updateTotalForms('form', 1);
                    $('#id_form-INITIAL_FORMS').val(parseInt(personaCount, 10) + '');

                    goToPersona(i, 500);
                    ajaxLockFlag = 0;
                });
            }

            var keymap = {
                j: ['next', null],
                k: ['prev', null],
                a: ['approve', null],
                r: ['reject_reason', null],
                d: ['duplicate', null],
                f: ['flag', null],
                m: ['moreinfo', null]
            };
            for (var j = 0; j <= 9; j++) {
                keymap[j] = ['reject_reason_detail', j];
            }

            function setReviewed(i, text) {
                $(nthPersona(i)).addClass('reviewed');
                $('.status', personas[i].element).addClass('reviewed').text(text);
                $('#reviewed-count').text($('div.persona.reviewed').length);
                if ($(queue).hasClass('advance')) {
                    goToPersona(i+1, 500);
                } else {
                    delete keymap[z.keys.ENTER];
                    $('.rq-dropdown').hide();
                }
                if ($('#reviewed-count').text() == $('#total').text()) {
                    morePersonas();
                }
            }

            var isRejecting = false;
            $('li.reject_reason').click(function(e) {
                if (!isRejecting) {
                    var rejectId = $(this).data('id');
                    reject_reason_detail(i, rejectId);
                }
            });

            var personaActions = {
                next: function (i) { goToPersona(i+1); },
                prev: function (i) { goToPersona(i-1); },

                approve: function (i) {
                    $('input.action', nthPersona(i)).val(4);
                    setReviewed(i, 'Approved');
                },

                reject_reason: function (i) {
                    // Open up dropdown of rejection reasons and set up
                    // key and click-bindings for choosing a reason. This
                    // function does not actually do the rejecting as the
                    // rejecting is only done once a reason is supplied.
                    $('.rq-dropdown:not(.reject-reason-dropdown)').hide();
                    $('.reject-reason-dropdown', nthPersona(i)).toggle();
                    isRejecting = true;
                },

                reject_reason_detail: function(i, rejectId) {
                    if (!isRejecting) { return; }

                    $('.rq-dropdown:not(.reject-reason-detail-dropdown)').hide();
                    $('.reject-reason-detail-dropdown', nthPersona(i)).toggle();
                    var textArea = $('.reject-reason-detail-dropdown textarea', nthPersona(i)).focus();

                    // Submit link/URL of the duplicate.
                    var submit = function() {
                        if (textArea.val()) {
                            $('input.comment', nthPersona(i)).val(textArea.val());
                            textArea.blur();
                            personaActions.reject(i, rejectId);
                        } else {
                            $('.reject-reason-detail-dropdown .error-required').show();
                        }
                    };
                    keymap[z.keys.ENTER] = submit;
                    $('.reject-reason-detail-dropdown button').click(_pd(submit));
                },

                reject: function(i, rejectId) {
                    // Given the rejection reason, does the actual rejection of
                    // the Persona.
                    $('input.action', nthPersona(i)).val(3);
                    $('input.reject-reason', nthPersona(i)).val(rejectId);
                    setReviewed(i, 'Rejected');
                    isRejecting = false;
                },

                duplicate: function(i) {
                    // Open up dropdown to enter ID/URL of duplicate.
                    $('.rq-dropdown:not(.duplicate-dropdown)').hide();
                    $('.duplicate-dropdown', nthPersona(i)).toggle();
                    var textArea = $('.duplicate-dropdown textarea', nthPersona(i)).focus();

                    // Submit link/URL of the duplicate.
                    var submit = function() {
                        if (textArea.val()) {
                            $('input.action', nthPersona(i)).val(2);
                            $('input.comment', nthPersona(i)).val(textArea.val());
                            textArea.blur();
                            setReviewed(i, 'Duplicate');
                        } else {
                            $('.duplicate-dropdown .error-required').show();
                        }
                    };
                    keymap[z.keys.ENTER] = submit;
                    $('.duplicate-dropdown button').click(_pd(submit));
                },

                flag: function(i) {
                    // Open up dropdown to enter reason for flagging.
                    $('.rq-dropdown:not(.flag-dropdown)').hide();
                    $('.flag-dropdown', nthPersona(i)).toggle();
                    var textArea = $('.flag-dropdown textarea', nthPersona(i)).focus();

                    // Submit link/URL of the flag.
                    var submit = function() {
                        if (textArea.val()) {
                            $('input.action', nthPersona(i)).val(1);
                            $('input.comment', nthPersona(i)).val(textArea.val());
                            textArea.blur();
                            setReviewed(i, 'Flagged');
                        } else {
                            $('.flag-dropdown .error-required').show();
                        }
                    };
                    keymap[z.keys.ENTER] = submit;
                    $('.flag-dropdown button').click(_pd(submit));
                },

                moreinfo: function(i) {
                    // Open up dropdown to enter ID/URL of moreinfo.
                    $('.rq-dropdown:not(.moreinfo-dropdown)').hide();
                    $('.moreinfo-dropdown', nthPersona(i)).toggle();
                    var textArea = $('.moreinfo-dropdown textarea', nthPersona(i)).focus();

                    // Submit link/URL of the moreinfo.
                    var submit = function() {
                        if (textArea.val()) {
                            $('input.action', nthPersona(i)).val('0');
                            $('input.comment', nthPersona(i)).val(textArea.val());
                            textArea.blur();
                            setReviewed(i, 'Requested Info');
                        } else {
                            $('.moreinfo-dropdown .error-required').show();
                        }
                    };
                    keymap[z.keys.ENTER] = submit;
                    $('.moreinfo-dropdown button').click(_pd(submit));
                }
            };

            $('button.approve', this).click(_pd(function(e) {
                personaActions.approve(getPersonaParent(e.currentTarget));
            }));
            $('button.reject', this).click(_pd(function(e) {
                personaActions.reject_reason(getPersonaParent(e.currentTarget));
            }));
            $('button.duplicate', this).click(_pd(function(e) {
                e.preventDefault(); // _pd wasn't working...
                personaActions.duplicate(getPersonaParent(e.currentTarget));
            }));
            $('button.flag', this).click(_pd(function(e) {
                personaActions.flag(getPersonaParent(e.currentTarget));
            }));
            $('button.moreinfo', this).click(_pd(function(e) {
                personaActions.moreinfo(getPersonaParent(e.currentTarget));
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
                var details = true;  // $('#rq-details:checked', self).val() */
                var advance = $('#rq-advance:checked', self).val();
                var single = true;  // $('#rq-single:checked', self).val()
                var shortcuts = true;  // $('#rq-shortcuts:checked', self).val()

                $(queueSelector)
                    .toggleClass('details', !!details)
                    .toggleClass('advance', !!advance)
                    .toggleClass('single', !!single)
                    .toggleClass('shortcuts', !!shortcuts);

                $('.shortcuts', self).toggle(shortcuts);
            }
        });
    };
})(jQuery);


$(document).ready(function() {
    $('.zoombox').zoomBox();
    $('.persona-queue').personaQueue();
    $('.sidebar').personaQueueOptions('.persona-queue');
    $('button#commit', this).click(_pd(function(e) {
        $('#persona-queue-form').submit();
    }));
});
