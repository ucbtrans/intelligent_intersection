function [ppt,op]=openppt(filespec,doerase)
% [ppt,op]=openppt(filespec,doerase)

if(~exist([filespec '.ppt'],'file') | doerase)
    [s,r]=system(['copy /y ppttemplate.ppt ' filespec '.ppt']);
    doerase  = 0;
end


% Establish valid file name:
if nargin<1 | isempty(filespec);
    [fname, fpath] = uiputfile('*.ppt');
    if fpath == 0; return; end
    filespec = fullfile(fpath,fname);
else
    [fpath,fname,fext] = fileparts(filespec);
    if isempty(fpath); fpath = pwd; end
    if isempty(fext); fext = '.ppt'; end
    filespec = fullfile(fpath,[fname,fext]);
end

% Start an ActiveX session with PowerPoint:
ppt = actxserver('PowerPoint.Application');

if ~exist(filespec,'file');
    % Create new presentation:
    op = invoke(ppt.Presentations,'Add');
else
    if nargin<2
        doerase=input('Erase old ppt? ')
    end
    if doerase
        delete(filespec)
        % Create new presentation:
        op = invoke(ppt.Presentations,'Add');
    else
        % Open existing presentation:
        op = invoke(ppt.Presentations,'Open',filespec,[],[],0);
    end
end

if ~exist(filespec,'file')
    % Save file as new:
    invoke(op,'SaveAs',filespec,1);
else
    % Save existing file:
    invoke(op,'Save');
end

return