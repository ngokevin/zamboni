
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
	$.fn.themeQueue = function() {
		return this.each(function() {
			var queue = this;
			var currenttheme = 0;
			var cacheQueueHeight;

			var themes = $('.theme', queue).map(function() {
				return {
					element: this,
					top: 0
				};
			}).get();

			$(window).scroll(function() {
				updateMetrics();
				var i = findCurrenttheme();
				if (i != currenttheme) {
					switchtheme( findCurrenttheme() );
				}
			});

			$('.theme .choices button', this).click(function(e) {
				var i = getthemeParent(e.currentTarget);
				themeActions.approve(i);
				return false;
			});

			$(document).keyup(function(e) {
				if (!$(queue).hasClass('shortcuts')) return;

				var key = String.fromCharCode(e.which).toLowerCase();
				var action = keymap[key];
				if (action && !e.ctrlKey && !e.altKey && !e.metaKey) {
					themeActions[action](currenttheme);
					return false;
				}
			});

			$('.theme', queue).removeClass('active');
			updateMetrics();
			switchtheme( findCurrenttheme() );


			function updateMetrics()
			{
				var queueHeight = $(queue).height();
				if (queueHeight === cacheQueueHeight) return;
				cacheQueueHeight = queueHeight;

				$.each(themes, function(i, obj) {
					var elem = $(obj.element);
					obj.top = elem.offset().top + elem.outerHeight()/2;
				});
			}

			function getthemeParent(elem)
			{
				var parent = $(elem).closest('.theme').get(0);
				for (var i = 0; i < themes.length; i++) {
					if (themes[i].element == parent) {
						return i;
					}
				}
				return -1;
			}

			function gototheme(i, delay, duration)
			{
				delay = delay || 0;
				duration = duration || 250;

				setTimeout(function() {
					if (i < 0) {
						alert('Previous Page');
					} else if (i >= themes.length) {
						alert('Next Page');
					} else {
						$(themes[i].element).scrollTo({ duration: duration, marginTop: 20 });
					}
				}, delay);
			}

			function switchtheme(i)
			{
				$(themes[currenttheme].element).removeClass('active');
				$(themes[i].element).addClass('active');
				currenttheme = i;
			}

			function findCurrenttheme()
			{
				var pageTop = $(window).scrollTop();

				if (pageTop <= themes[currenttheme].top) {
					for (var i = currenttheme-1; i >= 0; i--) {
						if (themes[i].top < pageTop) {
							break;
						}
					}
					return i+1;
				}

				else {
					for (var i = currenttheme; i < themes.length-1; i++) {
						if (pageTop <= themes[i].top) {
							break;
						}
					}
					return i;
				}
			}


			var themeActions = {
				'next': function (i) { gototheme(i+1); },
				'prev': function (i) { gototheme(i-1); },

				'approve': function (i) {
					$('.status', themes[i].element).addClass('reviewed');

					if ($(queue).hasClass('advance')) {
						gototheme(i+1, 500);
					}
				}
			};

			var keymap = {
				'j': 'next',
				'k': 'prev',
				'a': 'approve',
				'r': 'approve',
				'd': 'approve',
				'f': 'approve',
				'm': 'approve'
			};
		});
	};

	$.fn.themeQueueOptions = function(queueSelector) {
		return this.each(function() {
			var self = this;

			$('input', self).click(onChange);
			$('select', self).change(onChange);
			onChange();

			function onChange(e)
			{
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
	$('.theme-queue').themeQueue();
	$('.sidebar').themeQueueOptions('.theme-queue');
});
