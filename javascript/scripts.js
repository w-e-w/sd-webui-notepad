function notepadConfirmRename (name, dummy) {
    if (name === null || name.match(/^ *$/) !== null) return [null, null];
    let newName = prompt("Enter new notepad name for \"" + name + "\"")
    return [name, newName]
}

function notepadConfirmDelete (name, version) {
    if (name === null || name.match(/^ *$/) !== null) return [null, null];
    return (confirm("Do you wish to delete \"" + name + " - " + version+ "\"")) ? [name, version] : [null, null];
}
