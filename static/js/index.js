$(document).ready(function () {
  // Each choice carries its video path in data-video; an empty path shows the placeholder.
  var player = $('#result-video');
  var placeholder = $('#video-placeholder');
  $('#video-picker .video-choice').click(function () {
    $('#video-picker .video-choice').removeClass('is-active');
    $(this).addClass('is-active');
    var src = $(this).data('video');
    player[0].pause();
    player.prop('hidden', !src).attr('src', src || null);
    placeholder.prop('hidden', !!src);
    if (src) player[0].play();
  });
});
