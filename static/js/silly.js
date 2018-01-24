var board;
var game = new Chess();

var curid;
var sourceid;
var moves;
var movenr = 0;
var fail = false;
var fail_timer;
var debugdata;

var cfg;

var startfen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

function time_up(){
    $('#message').text('Time is up!');
    $('#status').text('Failed');
    fail = true;
}

function getNext(data){
    var fact = $.parseJSON(data['fact']);

    debugdata = data;
    curid = data['key'];
    console.log('id is ' + curid);
    console.log(fact);
    moves = fact['moves'];

    if(fact.hasOwnProperty('fen')){
        reset(fact.fen);
        clearTimeout(fail_timer);
        fail_timer = setTimeout(time_up, 35000);
        delayedAutoMove(5000);
    } else {
        reset(startfen);
        delayedAutoMove(1000);
    }

    if(fact.orientation == 'b')
        board.orientation('black');

    $.ajax({url: "/source/" + sourceid + "/stat", success: function(stat){
        var dt = new Date(stat['next'] * 1000);

        var localnext = new Date(dt.getTime() - (dt.getTimezoneOffset() * 60000));
        mess = stat['left'] + ' / ' + stat['total'] + ' due, next: ' + localnext.toISOString();
        $('#message').text(mess);
    }, cache: false});
}

function nextUrl(){
    var suffix = 'success';
    if(fail) suffix = 'fail';
    return '/source/' + sourceid + '/' + curid + '/' + suffix;
}

function reset(fen){
    board = ChessBoard('board', cfg);
    board.position(fen);
    game = new Chess(fen);
    movenr = 0;
    fail = false;
    $('#message').html('&nbsp;');
    $('#status').html('&nbsp;');
    $('#comment').text('');
    $('#pgn').text('');
}


function delayedAutoMove(delay=100){
    setTimeout(maybeAutoMove, delay);
}

function maybeAutoMove(){
    if(movenr == moves.length){
        clearTimeout(fail_timer);
        $('#message').html("<a onclick='$.post(nextUrl(), getNext)' href='#" + sourceid + "'>Next!</a>");
        return;
    }
    if(moves[movenr]['ask']){
        return;
    }
    game.move(moves[movenr].move, {sloppy: true});
    board.position(game.fen());
    movenr++;
    $('#pgn').text(game.pgn());
    delayedAutoMove();
}

var removeGreySquares = function() {
  $('#board .square-55d63').css('background', '');
};

var greySquare = function(square) {
  var squareEl = $('#board .square-' + square);

  var background = '#a9a9a9';
  if (squareEl.hasClass('black-3c85d') === true) {
    background = '#696969';
  }

  squareEl.css('background', background);
};

var onDragStart = function(source, piece) {
  // do not pick up pieces if the game is over
  // or if it's not that side's turn
  if (game.game_over() === true ||
      (game.turn() === 'w' && piece.search(/^b/) !== -1) ||
      (game.turn() === 'b' && piece.search(/^w/) !== -1)) {
    return false;
  }
};

var onDrop = function(source, target) {
    removeGreySquares();

    // see if the move is legal
    var move = game.move({
        from: source,
        to: target,
        promotion: 'q' // TODO: promotion choice
    });

    if (move === null) return 'snapback';

    if(move.san != moves[movenr].move){
        if($.inArray(move.san, moves[movenr].ok) != -1){
            $('#message').text('Good move, but try another');
        } else {
            clearTimeout(fail_timer);
            $('#message').text('Expected ' + moves[movenr].move);
            $('#status').text('Failed');
            fail = true;
            console.log(move.san + " != " + moves[movenr].move);
        }
        game.undo();
        return 'snapback';
    }
    $('#message').html('&nbsp;');
    if (moves[movenr].comment)
        $('#comment').text(moves[movenr].comment);
    else
        $('#comment').text('');

    movenr++;
    delayedAutoMove();
};

var onMouseoverSquare = function(square, piece) {
  // get list of possible moves for this square
  var moves = game.moves({
    square: square,
    verbose: true
  });

  // exit if there are no moves available for this square
  if (moves.length === 0) return;

  // highlight the square they moused over
  greySquare(square);

  // highlight the possible squares for this piece
  for (var i = 0; i < moves.length; i++) {
    greySquare(moves[i].to);
  }
};

var onMouseoutSquare = function(square, piece) {
  removeGreySquares();
};

var onSnapEnd = function() {
    board.position(game.fen());
    $('#pgn').text(game.pgn());
};

cfg = {
    draggable: true,
    position: 'start',
    onDragStart: onDragStart,
    onDrop: onDrop,
    onMouseoutSquare: onMouseoutSquare,
    onMouseoverSquare: onMouseoverSquare,
    onSnapEnd: onSnapEnd
};

$( document ).ready(function(){
    function preventBehavior(e) {
        e.preventDefault();
    };

    document.addEventListener("touchmove", preventBehavior, false);
    sourceid = window.location.hash.substr(1);
    console.log(sourceid);
    $.get("/source/" + sourceid + "/next", getNext);
});

//Make adaptive with this
function adjustStyle(width) {
    width = parseInt(width);
    if (width < 701) {
        $("#size-stylesheet").attr("href", "css/narrow.css");
    } else if (width < 900) {
        $("#size-stylesheet").attr("href", "css/medium.css");
    } else {
        $("#size-stylesheet").attr("href", "css/wide.css");
    }
}
