var board;
var game = new Chess();

var curid;
var sourceid = '6192449487634432';
var moves;
var movenr = 0;
var fail = false;
var debugdata;

var cfg;

function getNext(data){
    reset();
    var fact = $.parseJSON(data['fact']);
    debugdata = data;
    curid = data['key'];
    moves = fact['moves'];
    if(fact.orientation == 'b')
        board.orientation('black');

    maybeAutoMove();
}

function nextUrl(){
    var suffix = 'success';
    if(fail) suffix = 'fail';
    return '/source/' + sourceid + '/' + curid + '/' + suffix;
}

function reset(){
    board = ChessBoard('board', cfg);
    game = new Chess();
    movenr = 0;
    fail = false;
    $('#message').html('&nbsp;');
    $('#status').html('&nbsp;');
    $('#comment').text('');
    $('#pgn').text('');
}


function delayedAutoMove(){
    setTimeout(maybeAutoMove, 100);
}

function maybeAutoMove(){
    if(movenr == moves.length){
        $('#message').html("<a onclick='$.post(nextUrl(), getNext)' href='#'>Next!</a>");
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
