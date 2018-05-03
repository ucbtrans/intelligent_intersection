function [vidObj]=DisplayVideoOct(h, vidObj,oldt,CurrentDate, CurrentTime, EventsDayRadars, BoundariesRadar, ...
    PhasesDay,BoundariesPhases, EventsDayMag, BoundariesMag, IDsRadar, IDsMag)
    
%% Defining parameters and the physics of the model (Sensors from the file loaded below)
load('RadarsProperties');
ZoneShape = Sensors{6};

    
    %% Extract the RAdars events within ped phase 14
    list=0*ones(8,2);
    list(1,1)=-1;
    list(8,1)=-1;
    list(4,1)=-1;
    list(4,2)=-1;
    set=[[1,2];[2,1];[2,2];[3,1];[3 2];[4 1];[5 1];[5 2];[6 1];[6 2];[7 1];[7 2];[8 2];];
%     list=-1*ones(length(IDsRadar),1);
%     for i = 1:length(IDsRadar) 
%         if length(EventsDayRadars(i).TimeDetect)>0
%             x=find((EventsDayRadars(i).TimeDetect<= CurrentTime).*( EventsDayRadars(i).TimeUndetect>=CurrentTime));
% %             disp(length(x));
%             if length(x)>0
%                 list(9-set(i,1),set(i,2))=111*length(x);
% %                 disp(x);
%             end
%         end
%     end
    
    
%     subplot('Position',[.05 .05 .4 .5]);
%     t = uitable('Parent', h, 'Position', [.05 .05 .4 .5], 'Data', [IDsRadar' num2cell(list)]);
%     t = uitable('Position',[100 640 200 250],'Data', num2cell(list));
    
    %%% reading video files

    t22=1429660800+3600*15+2*60+19.75;


    if CurrentTime>=t22 && CurrentTime<(t22+3600)

        if ~(oldt>=t22 && oldt<(t22+3600))
            tt=CurrentTime+3600*7;

            vidObj = VideoReader(['20150422_2.mp4']);

            vidHeight = vidObj.Height;
            vidWidth = vidObj.Width;
        end
        %     s = struct('cdata',zeros(vidHeight,vidWidth,3,'uint8'),...
        %     'colormap',[]);
        baset=floor((CurrentTime-140)/300)*300+140;clc;
        fno=floor((CurrentTime-t22)*10)+1
        i = read(vidObj,fno);
        
        figure(h);
        subplot('Position',[.07 .63 .35 .35]);
        cla();
        image(i)
%     else
%         if CurrentTime>=t24 && CurrentTime<(t24+3600)
%             %         tdiffo=oldt-t22;
%             %         tdiffn=CurrentTime -t22;
%             if ~(oldt>=t24 && oldt<(t24+3600))
%                 tt=CurrentTime+3600*7;
%                 file=['G:\TSC\Grants\G2015_Multimodal_Safety_Dynamics\Analysis\Videos\20150424_2.mp4']
%                 vidObj = VideoReader(['G:\TSC\Grants\G2015_Multimodal_Safety_Dynamics\Analysis\Videos\20150424_2.mp4']);
%                 vidHeight = vidObj.Height;
%                 vidWidth = vidObj.Width;
%             end
%             %     s = struct('cdata',zeros(vidHeight,vidWidth,3,'uint8'),...
%             %     'colormap',[]);
%             baset=floor((CurrentTime-140)/300)*300+140;clc;
%             fno=floor((CurrentTime-t24)*10)+1
%             i = read(vidObj,fno);
%             
%             figure(h);
%             subplot('Position',[.07 .63 .35 .35]);
%             cla();
%             image(i)
%         else
%             vidObj=1;
%             subplot('Position',[.07 .63 .35 .35]);
%             cla();
%         end
    end
    

    
    
%     k=subimage(i);
%     axes('Position',[.05 .05 .4 .5]);
    
    
    
    
    
    
end
    