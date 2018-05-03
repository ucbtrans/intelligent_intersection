function closeppt(ppt,op)
% closeppt(ppt,op)

invoke(op,'Save');

% Close the presentation window:
invoke(op,'Close');

% Quit PowerPoint
invoke(ppt,'Quit');

return