function handleFiles(source, files){
    function upload(color){
        var reader = new FileReader();
        reader.onload = (function(e) { $.post('/source/' + source + '/opening',
                                              {pgn: e.target.result, color: color},
                                              function(data){
                                                  displayStat(source);
                                              }
                                             );});
        console.log(color);
        reader.readAsText(files[0]);
        $('#input' + source).val('');
    }

    $( "#color-confirm" ).dialog({
        resizable: false,
        width: 400,
        modal: true,
        buttons: {
            White: function() {
                upload('w');
                $( this ).dialog( "close" );
            },
            Black: function() {
                upload('b');
                $( this ).dialog( "close" );
            }
        }
    });
}

function displayStat(source){
    $.ajax({url: "/source/" + source + "/stat", success: function(stat){
        var dt = new Date(stat['next'] * 1000);

        var localnext = new Date(dt.getTime() - (dt.getTimezoneOffset() * 60000));
        if(stat['total'])
            $('#stat' + stat['key']).html(': ' + stat['left'] + ' / ' + stat['total'] + ' due, <a href="/board#'+source+'">next: ' + localnext.toISOString() +'</a>');
        else
            $('#stat' + stat['key']).text(': ' + stat['left'] + ' / ' + stat['total'] + ' due');
    }, cache: false});
}

function displaySource(source){
    $('#sourcelist').append('<div id="'+source['key']+'">' + source['name'] + '<span id="stat' + source['key'] + '"></span><div>' +
                            '<a href="#" onclick="deleteSource(' + source['key'] + ')">Delete</a> ' +
                            '<input type="file" id="input'+source['key']+'" onchange="handleFiles('+source['key']+', this.files)">' +
                            '</div><p/>');
    displayStat(source['key']);
}

function getSources(data){
    $(data['sources']).each(function(i, source){
        displaySource(source);
    });
}

function deleteSource(source){
    var name = $('#'+source).text();
    $( "#delete-confirm" ).dialog({
        resizable: false,
        width: 400,
        modal: true,
        buttons: {
            "Delete source": function() {
                $.ajax({
                    url: '/source/' + source,
                    type: 'DELETE',
                    success: function(result) {
                        $('#' + source).remove();
                    }});
                $( this ).dialog( "close" );
            },
            Cancel: function() {
                $( this ).dialog( "close" );
            }
        }
    });
}

function addSource(){
    var name = $('#addsource').val();
    if(name == ""){
        $( "#noname-message" ).dialog({
            modal: true,
            width: 400,
            buttons: {
                Ok: function() {
                    $( this ).dialog( "close" );
                }
            }
        });
    } else {
        $.post("/source", {name: name, fact_type: 'opening'}, function(data){
            $('#addsource').val('');
            $.ajax({url: "/source/" + data.key, success: displaySource, cache: true});
        });
    }
}

$( document ).ready(function(){
    $( "#noname-message" ).hide();
    $( "#color-confirm" ).hide();
    $( "#delete-confirm" ).hide();
    $('#addbutton').click(addSource);
    $.ajax({url: "/source", success: getSources, cache: false});
});
